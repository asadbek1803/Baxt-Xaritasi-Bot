from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models import TelegramUser, ReferralPayment
from bot.selectors import create_referral_payment_request
from bot.buttons.default.back import get_back_keyboard
from asgiref.sync import sync_to_async

router = Router()

class ReferralPaymentState(StatesGroup):
    WAITING_FOR_SCREENSHOT = State()

# 1. Referral to'lov so'rovi yaratish va foydalanuvchiga rekvizitlarni chiqarish
@router.callback_query(F.data.startswith("create_referral_"))
async def create_referral(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    # select_related yoki prefetch_related ishlatish
    user = await TelegramUser.objects.select_related('invited_by').filter(telegram_id=user_id).afirst()
    
    if not user or not user.invited_by:
        return await callback.answer("❌ Sizda referral egasi topilmadi!", show_alert=True)

    referrer = user.invited_by
    
    # Referral to'lov so'rovi yaratish
    referral_payment = await create_referral_payment_request(
        user_id=user_id,
        referrer_id=referrer.telegram_id,
        amount=200_000
    )
    if not referral_payment:
        return await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)

    # Foydalanuvchiga rekvizitlar va "To'lov qildim" tugmasi
    payment_info_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'lov qildim", callback_data=f"payment_made_{referral_payment.id}")]
    ])
    await callback.message.answer(
        "💡 Referral tizimi haqida:\n\n"
        "1️⃣ Siz avval 200,000 so'm to'lovni amalga oshirishingiz kerak\n"
        "2️⃣ To'lov tasdiqlangach, sizga maxsus referral kod beriladi\n"
        "3️⃣ Bu kod orqali boshqalarni taklif qilganingizda:\n"
        "   - Ular ham 200,000 so'm to'lashadi\n"
        "   - Siz har bir taklif qilgan odamingizdan 200,000 so'm ishlaysiz!\n\n"
        "💳 To'lov uchun karta ma'lumotlari:\n"
        f"Karta: {referrer.card_number}\n"
        f"Karta egasi: {referrer.card_holder_full_name}\n\n"
        "To'lov qilganingizdan so'ng pastdagi tugmani bosing:",
        reply_markup=payment_info_keyboard
    )
    await callback.answer()

# 2. "To'lov qildim" tugmasi bosilganda foydalanuvchidan chek so'rash
@router.callback_query(F.data.startswith("payment_made_"))
async def referral_payment_made(callback: types.CallbackQuery, state: FSMContext):
    payment_id = callback.data.split("_")[-1]
    await state.update_data(referral_payment_id=payment_id)
    await state.set_state(ReferralPaymentState.WAITING_FOR_SCREENSHOT)
    await callback.message.answer(
        "✅ To'lovni amalga oshirganingiz uchun rahmat!\n\n"
        "Iltimos, to'lov chekini (screenshot) yuboring.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

# 3. Chek kelganda uni referrerga yuborish va tasdiqlash/ rad etish tugmalari
@router.message(ReferralPaymentState.WAITING_FOR_SCREENSHOT)
async def process_referral_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    global xabar
    payment_id = data.get("referral_payment_id")
    user_id = str(message.from_user.id)
    user = await TelegramUser.objects.filter(telegram_id=user_id).afirst()
    
    # select_related ishlatish
    payment = await ReferralPayment.objects.select_related('referrer', 'user').filter(id=payment_id).afirst()
    
    if not payment or not user:
        await message.answer("Xatolik! To'lov yoki foydalanuvchi topilmadi.")
        return

    # Rasmni saqlash (file_id yoki yuklab olingan fayl yo'li)
    photo = message.photo[-1]
    
    # Agar modelda screenshot maydoni bo'lsa
    if hasattr(payment, 'screenshot'):
        payment.screenshot = photo.file_id
        payment.status = 'PENDING'
        await payment.asave(update_fields=['screenshot', 'status'])
    else:
        # Agar screenshot maydoni yo'q bo'lsa, faqat status ni yangilash
        payment.status = 'PENDING'
        await payment.asave(update_fields=['status'])

    # Taklif qilgan userga (referrer) yuborish
    referrer = payment.referrer
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, tasdiqlash", callback_data=f"confirm_referral_{payment.id}")],
        [InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data=f"reject_referral_{payment.id}")]
    ])
    try:
        xabar = await message.bot.send_photo(
            chat_id=referrer.telegram_id,
            photo=photo.file_id,
            caption=(
                f"💰 Sizni taklif qilgan foydalanuvchi to'lov chekini yubordi!\n\n"
                f"👤 Foydalanuvchi: {user.full_name}\n"
                f"💳 Miqdor: {payment.amount} so'm\n\n"
                "To'lovni tasdiqlaysizmi?"
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error sending photo to referrer: {e}")

    await message.answer(
        "✅ To'lov cheki qabul qilindi! Taklif qilgan foydalanuvchiga yuborildi. U tasdiqlaganidan so'ng sizga xabar beriladi.",
        reply_markup=get_back_keyboard()
    )
    await state.clear()

# 4. Referrer tasdiqlasa yoki rad etsa
@router.callback_query(F.data.startswith("confirm_referral_"))
async def confirm_referral_payment(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[-1]
    user_id = str(callback.from_user.id)
    user = await TelegramUser.objects.filter(telegram_id=user_id).afirst()
    
    # select_related ishlatish
    payment = await ReferralPayment.objects.select_related('user').filter(id=payment_id).afirst()
    
    if not payment:
        return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
        
    payment.status = 'CONFIRMED'
    await payment.asave(update_fields=['status'])
    await xabar.delete()  # Referrerga yuborilgan xabarni o'chirish
    # User obyektini yangilash
    payment_user = payment.user
    
    # Referral code va link ni olish
    try:
        # Agar methodlar database query qilmasa, to'g'ridan-to'g'ri chaqirish mumkin
        
        referral_link = payment_user.get_referral_link()
    except Exception as e:
        print(f"Error getting referral info: {e}")
       
        referral_link = payment_user.get_referral_link()
    
    payment_user.is_confirmed = True
    await payment_user.asave(update_fields=['is_confirmed'])
    
    # Foydalanuvchiga xabar
    try:
        await callback.bot.send_message(
            chat_id=payment_user.telegram_id,
            text="🎉 Tabriklaymiz! Sizning referral to'lovingiz tasdiqlandi.\n\n"
                 "Endi siz ham o'z referral kodingiz orqali odam taklif qilishingiz mumkin!"
        )
        
        await callback.bot.send_message(
            chat_id=payment_user.telegram_id,
            text=f"🎯 Sizning Referral Ma'lumotlaringiz:\n\n"
            f"🆔 Referral ID: {payment_user.telegram_id}\n"
            f"👥 To'liq ismingiz: {payment_user.full_name}\n"
            f"💰 To'langan summa: {payment.amount:,} so'm\n"
            f"📅 To'lov vaqti: {payment.created_at.strftime('%d-%m-%Y %H:%M')}\n"
            f"✅ Status: Tasdiqlandi\n\n"
            f"🔗 Sizning referral havolangiz:\n"
            f"{referral_link}"
    )
    except Exception as e:
        print(f"Error sending confirmation: {e}")
    await callback.answer("✅ Referral to'lovi tasdiqlandi!", show_alert=True)

@router.callback_query(F.data.startswith("reject_referral_"))
async def reject_referral_payment(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[-1]
    
    # select_related ishlatish
    payment = await ReferralPayment.objects.select_related('user').filter(id=payment_id).afirst()
    
    if not payment:
        return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
    await xabar.delete()
    payment.status = 'REJECTED'
    await payment.asave(update_fields=['status'])
    
    # Foydalanuvchiga xabar
    try:
        await callback.bot.send_message(
            chat_id=payment.user.telegram_id,
            text="❌ Sizning referral to'lovingiz rad etildi. Iltimos, to'lovni tekshirib qayta urinib ko'ring."
        )
    except Exception as e:
        print(f"Error sending rejection: {e}")
    await callback.answer("❌ Referral to'lovi rad etildi!", show_alert=True)