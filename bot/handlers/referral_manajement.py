import asyncio
from functools import wraps
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models import TelegramUser, ReferralPayment
from bot.selectors import create_referral_payment_request, get_root_referrer
from bot.buttons.default.back import get_back_keyboard
from asgiref.sync import sync_to_async

router = Router()


class ReferralPaymentState(StatesGroup):
    WAITING_FOR_SCREENSHOT = State()


# Global variable to store message for deletion
xabar = None


def timeout(seconds=10):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                print(f"Timeout occurred in {func.__name__}")
                return None

        return wrapper

    return decorator


# 1. Referral to'lov so'rovi yaratish va foydalanuvchiga rekvizitlarni chiqarish
@router.callback_query(F.data.startswith("create_referral_"))
async def create_referral(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = str(callback.from_user.id)
        course_id = callback.data.split("_")[-1]

        # Get root referrer
        root_referrer = await get_root_referrer(user_id)
        if not root_referrer:
            await callback.answer(
                "❌ Referral tizimida muammo topildi! Admin bilan bog'laning.",
                show_alert=True,
            )
            return

        # Create referral payment
        try:
            referral_payment = await create_referral_payment_request(
                user_id=user_id, amount=200_000
            )
            if not referral_payment:
                await callback.answer(
                    "❌ To'lov so'rovi yaratishda xatolik!", show_alert=True
                )
                return
        except Exception as e:
            print(f"[create_referral] Error creating payment: {e}")
            await callback.answer(
                "❌ To'lov so'rovi yaratishda xatolik!", show_alert=True
            )
            return

        # Prepare payment info
        payment_info_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ To'lov qildim",
                        callback_data=f"payment_made_{referral_payment.id}",
                    )
                ]
            ]
        )

        card_number = getattr(root_referrer, "card_number", "Ma'lumot mavjud emas")
        card_holder = getattr(
            root_referrer, "card_holder_full_name", "Ma'lumot mavjud emas"
        )
        root_user_phone = getattr(root_referrer, "phone_number", "Ma'lumot mavjud emas!")
        root_user_telegram_username = getattr(root_referrer, "telegram_username", "Ma'lumot mavjud emas!")


        payment_text = (
            "💡 Referral tizimi haqida:\n\n"
            "1️⃣ Siz avval 200,000 so'm to'lovni amalga oshirishingiz kerak\n"
            "2️⃣ To'lov tasdiqlangach, sizga maxsus referral kod beriladi\n"
            "3️⃣ Bu kod orqali boshqalarni taklif qilganingizda:\n"
            "   - Ular ham 200,000 so'm to'lashadi\n"
            "   - To'lovlar to'g'ridan-to'g'ri admin hisobiga o'tadi va ular o'z referallarini tarqatish orqali sizga daromad olib keladi. Har bir ular chaqirgan referal 200 ming so'mdan sizga to'lov qilishadi.\n\n"
            "💳 To'lov uchun karta ma'lumotlari:\n"
            f"Telefon raqami: <code> {root_user_phone} </code>\n"
            f"Telegram profili: @{root_user_telegram_username}\n"
            f"Karta: <code>{card_number}</code>\n"
            f"Karta egasi: <b>{card_holder}</b>\n\n"
            "To'lov qilganingizdan so'ng pastdagi tugmani bosing:"
        )

        await callback.message.answer(
            text=payment_text, reply_markup=payment_info_keyboard, parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        print(f"[create_referral] Unexpected error: {e}")
        await callback.answer("❌ Kutilmagan xatolik yuz berdi!", show_alert=True)


# 2. "To'lov qildim" tugmasi bosilganda foydalanuvchidan chek so'rash
@router.callback_query(F.data.startswith("payment_made_"))
async def referral_payment_made(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_id = callback.data.split("_")[-1]
        await state.update_data(referral_payment_id=payment_id)
        await state.set_state(ReferralPaymentState.WAITING_FOR_SCREENSHOT)

        await callback.message.answer(
            "✅ To'lovni amalga oshirganingiz uchun rahmat!\n\n"
            "Iltimos, to'lov chekini (screenshot) yuboring.",
        )
        await callback.answer()

    except Exception as e:
        print(f"[referral_payment_made] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


# 3. Chek kelganda uni ADMINga yuborish va tasdiqlash/ rad etish tugmalari
@router.message(ReferralPaymentState.WAITING_FOR_SCREENSHOT)
async def process_referral_payment_screenshot(
    message: types.Message, state: FSMContext
):
    try:
        data = await state.get_data()
        payment_id = data.get("referral_payment_id")

        if not payment_id:
            await message.answer("❌ To'lov ma'lumotlari topilmadi. Qayta boshlang.")
            await state.clear()
            return

        if not message.photo:
            await message.answer("📷 Iltimos, to'lov chekining rasmini yuboring.")
            return

        # Get user and payment data with timeout
        try:
            user = await asyncio.wait_for(
                sync_to_async(TelegramUser.objects.get)(
                    telegram_id=str(message.from_user.id)
                ),
                timeout=10,
            )
            payment = await asyncio.wait_for(
                sync_to_async(
                    lambda: ReferralPayment.objects.select_related(
                        "referrer", "user"
                    ).get(id=payment_id)
                )(),
                timeout=10,
            )
        except (
            TelegramUser.DoesNotExist,
            ReferralPayment.DoesNotExist,
            asyncio.TimeoutError,
        ):
            await message.answer("❌ Ma'lumotlar topilmadi yoki vaqt tugadi.")
            await state.clear()
            return

        # Process screenshot and save
        photo = message.photo[-1]
        try:
            if hasattr(payment, "screenshot"):
                payment.screenshot = photo.file_id
            payment.status = "PENDING"
            await sync_to_async(payment.save)()
        except Exception as e:
            print(f"[process_screenshot] Error saving payment: {e}")
            await message.answer("❌ To'lov ma'lumotlarini saqlashda xatolik.")
            return

        # Store message info in state instead of global variable
        admin = payment.referrer
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Tasdiqlash",
                        callback_data=f"confirm_referral_{payment.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Rad etish",
                        callback_data=f"reject_referral_{payment.id}",
                    )
                ],
            ]
        )

        try:
            network_level = await get_network_level(str(message.from_user.id))
            caption = (
                f"💰 Yangi referral to'lov!\n\n"
                f"👤 Foydalanuvchi: {user.full_name} (ID: {user.telegram_id})\n"
                f"📊 Tarmoq darajasi: {network_level}-daraja\n"
                f"💳 Miqdor: {payment.amount:,} so'm\n\n"
                "To'lovni tasdiqlaysizmi?"
            )

            sent_message = await message.bot.send_photo(
                chat_id=admin.telegram_id,
                photo=photo.file_id,
                caption=caption,
                reply_markup=keyboard,
            )
            await state.update_data(admin_message_id=sent_message.message_id)
        except Exception as e:
            print(f"[process_screenshot] Error sending to admin: {e}")

        await message.answer(
            "✅ To'lov cheki qabul qilindi! Admin tasdiqlaganidan so'ng sizga xabar beriladi.",
            reply_markup=get_back_keyboard(),
        )
        await state.clear()

    except Exception as e:
        print(f"[process_screenshot] Unexpected error: {e}")
        await message.answer("❌ Kutilmagan xatolik yuz berdi.")
        await state.clear()


# Helper function to get network level
@sync_to_async
def get_network_level(user_id: str) -> int:
    """Foydalanuvchi tarmoqda qaysi darajada ekanligini aniqlash"""
    try:
        user = TelegramUser.objects.filter(telegram_id=user_id).first()
        if not user:
            return 0

        level = 0
        current = user
        while current.invited_by:
            level += 1
            current = current.invited_by
            # Infinite loop dan himoya qilish
            if level > 10:
                break

        return level
    except Exception as e:
        print(f"[get_network_level] Error: {e}")
        return 0


# 4. ADMIN tasdiqlasa yoki rad etsa
@router.callback_query(F.data.startswith("confirm_referral_"))
async def confirm_referral_payment(callback: types.CallbackQuery):
    try:
        payment_id = callback.data.split("_")[-1]

        # Get payment with related user
        try:
            payment = await sync_to_async(
                lambda: ReferralPayment.objects.select_related("user").get(
                    id=payment_id
                )
            )()
        except ReferralPayment.DoesNotExist:
            return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
        except Exception as e:
            print(f"[confirm_referral] Database error: {e}")
            return await callback.answer(
                "❌ Ma'lumotlar bazasida xatolik!", show_alert=True
            )

        # Update payment status
        try:
            payment.status = "CONFIRMED"
            await sync_to_async(payment.save)()
        except Exception as e:
            print(f"[confirm_referral] Error saving payment: {e}")
            return await callback.answer(
                "❌ To'lovni saqlashda xatolik!", show_alert=True
            )

        # Update user status and generate referral code if needed
        try:
            payment_user = payment.user
            if not payment_user.referral_code:
                payment_user.referral_code = str(payment_user.telegram_id)[-8:]  # Simple referral code
            payment_user.is_confirmed = True
            await sync_to_async(payment_user.save)()
        except Exception as e:
            print(f"[confirm_referral] Error updating user: {e}")
            # Continue even if user update fails

        # Send confirmation to user
        try:
            from core.settings import TELEGRAM_BOT_USERNAME

            referral_link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={payment_user.referral_code}"

            await callback.bot.send_message(
                chat_id=payment_user.telegram_id,
                text="🎉 Tabriklaymiz! Sizning referral to'lovingiz tasdiqlandi.\n\n"
                "Endi siz ham o'z referral kodingiz orqali odam taklif qilishingiz mumkin!",
            )
            await callback.bot.send_message(
                chat_id=payment_user.telegram_id,
                text=f"🎯 Sizning Referral Ma'lumotlaringiz:\n\n"
                f"🆔 Referral ID: {payment_user.telegram_id}\n"
                f"🔑 Referral kod: {payment_user.referral_code}\n"
                f"👥 To'liq ismingiz: {payment_user.full_name}\n"
                f"💰 To'langan summa: {payment.amount:,} so'm\n"
                f"📅 To'lov vaqti: {payment.created_at.strftime('%d-%m-%Y %H:%M')}\n"
                f"✅ Status: Tasdiqlandi\n\n"
                f"🔗 Sizning referral havolangiz:\n"
                f"{referral_link}",
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"[confirm_referral] Error sending confirmation: {e}")

        await callback.answer("✅ Referral to'lovi tasdiqlandi!", show_alert=True)

    except Exception as e:
        print(f"[confirm_referral] Unexpected error: {e}")
        await callback.answer("❌ Kutilmagan xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("reject_referral_"))
async def reject_referral_payment(callback: types.CallbackQuery):
    try:
        payment_id = callback.data.split("_")[-1]

        # Get payment with related user
        try:
            payment = await sync_to_async(
                lambda: ReferralPayment.objects.select_related("user").get(
                    id=payment_id
                )
            )()
        except ReferralPayment.DoesNotExist:
            return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
        except Exception as e:
            print(f"[reject_referral] Database error: {e}")
            return await callback.answer(
                "❌ Ma'lumotlar bazasida xatolik!", show_alert=True
            )

        # Delete the admin message
        global xabar
        if xabar:
            try:
                await xabar.delete()
            except:
                pass

        # Update payment status
        try:
            payment.status = "REJECTED"
            await sync_to_async(payment.save)()
        except Exception as e:
            print(f"[reject_referral] Error saving payment: {e}")
            return await callback.answer(
                "❌ To'lovni saqlashda xatolik!", show_alert=True
            )

        # Send rejection to user
        try:
            await callback.bot.send_message(
                chat_id=payment.user.telegram_id,
                text="❌ Sizning referral to'lovingiz rad etildi. Iltimos, to'lovni tekshirib qayta urinib ko'ring.",
            )
        except Exception as e:
            print(f"[reject_referral] Error sending rejection: {e}")

        await callback.answer("❌ Referral to'lovi rad etildi!", show_alert=True)

    except Exception as e:
        print(f"[reject_referral] Unexpected error: {e}")
        await callback.answer("❌ Kutilmagan xatolik yuz berdi!", show_alert=True)
