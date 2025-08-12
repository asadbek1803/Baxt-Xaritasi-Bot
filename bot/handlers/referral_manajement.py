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

# 1. Referral to'lov so'rovi yaratish va foydalanuvchiga rekvizitlarni chiqarish
@router.callback_query(F.data.startswith("create_referral_"))
async def create_referral(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    # Get root referrer (admin)
    root_referrer = await get_root_referrer(user_id)
    
    if not root_referrer:
        return await callback.answer("❌ Referral tizimida muammo topildi! Admin bilan bog'laning.", show_alert=True)

    # Referral to'lov so'rovi yaratish (avtomatik ravishda root referrerga)
    referral_payment = await create_referral_payment_request(
        user_id=user_id,
        amount=200_000  # Amount is now passed directly, referrer is determined automatically
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
        "   - To'lovlar to'g'ridan-to'g'ri admin hisobiga o'tadi\n\n"
        "💳 To'lov uchun karta ma'lumotlari:\n"
        f"Karta: {root_referrer.card_number}\n"
        f"Karta egasi: {root_referrer.card_holder_full_name}\n\n"
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

# 3. Chek kelganda uni ADMINga yuborish va tasdiqlash/ rad etish tugmalari
@router.message(ReferralPaymentState.WAITING_FOR_SCREENSHOT)
async def process_referral_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    global xabar
    payment_id = data.get("referral_payment_id")
    user_id = str(message.from_user.id)
    user = await TelegramUser.objects.filter(telegram_id=user_id).afirst()
    
    # Get payment with related data
    payment = await ReferralPayment.objects.select_related('referrer', 'user').filter(id=payment_id).afirst()
    
    if not payment or not user:
        await message.answer("Xatolik! To'lov yoki foydalanuvchi topilmadi.")
        return

    # Save screenshot (file_id or file path)
    photo = message.photo[-1]
    
    # Update payment with screenshot if field exists
    if hasattr(payment, 'screenshot'):
        payment.screenshot = photo.file_id
        payment.status = 'PENDING'
        await payment.asave(update_fields=['screenshot', 'status'])
    else:
        # If no screenshot field, just update status
        payment.status = 'PENDING'
        await payment.asave(update_fields=['status'])

    # Send to ADMIN (root referrer) for confirmation
    admin = payment.referrer  # This is already the root referrer
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_referral_{payment.id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_referral_{payment.id}")]
    ])
    
    try:
        xabar = await message.bot.send_photo(
            chat_id=admin.telegram_id,
            photo=photo.file_id,
            caption=(
                f"💰 Yangi referral to'lov!\n\n"
                f"👤 Foydalanuvchi: {user.full_name} (ID: {user.telegram_id})\n"
                f"📊 Tarmoq darajasi: {await get_network_level(user_id)}-daraja\n"
                f"💳 Miqdor: {payment.amount:,} so'm\n\n"
                "To'lovni tasdiqlaysizmi?"
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error sending photo to admin: {e}")

    await message.answer(
        "✅ To'lov cheki qabul qilindi! Admin tasdiqlaganidan so'ng sizga xabar beriladi.",
        reply_markup=get_back_keyboard()
    )
    await state.clear()

# Helper function to get network level
@sync_to_async
def get_network_level(user_id: str) -> int:
    """Foydalanuvchi tarmoqda qaysi darajada ekanligini aniqlash"""
    user = TelegramUser.objects.filter(telegram_id=user_id).first()
    if not user:
        return 0
    
    level = 0
    current = user
    while current.invited_by:
        level += 1
        current = current.invited_by
    
    return level

# 4. ADMIN tasdiqlasa yoki rad etsa
@router.callback_query(F.data.startswith("confirm_referral_"))
async def confirm_referral_payment(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[-1]
    
    # Get payment with related user
    payment = await ReferralPayment.objects.select_related('user').filter(id=payment_id).afirst()
    
    if not payment:
        return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
        
    # Update payment status
    payment.status = 'CONFIRMED'
    await payment.asave(update_fields=['status'])
    
    # Delete the admin message
    global xabar
    if xabar:
        try:
            await xabar.delete()
        except:
            pass
    
    # Update user status and generate referral code if needed
    payment_user = payment.user
    if not payment_user.referral_code:
        payment_user.referral_code = str(payment_user.telegram_id)[-8:]  # Simple referral code
        payment_user.is_confirmed = True
        await payment_user.asave(update_fields=['referral_code', 'is_confirmed'])
    
    # Send confirmation to user
    try:
        referral_link = f"https://t.me/your_bot_username?start={payment_user.telegram_id}"
        
        await callback.bot.send_message(
            chat_id=payment_user.telegram_id,
            text="🎉 Tabriklaymiz! Sizning referral to'lovingiz tasdiqlandi.\n\n"
                 "Endi siz ham o'z referral kodingiz orqali odam taklif qilishingiz mumkin!"
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
            f"{referral_link}"
        )
    except Exception as e:
        print(f"Error sending confirmation: {e}")
    
    await callback.answer("✅ Referral to'lovi tasdiqlandi!", show_alert=True)

@router.callback_query(F.data.startswith("reject_referral_"))
async def reject_referral_payment(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[-1]
    
    # Get payment with related user
    payment = await ReferralPayment.objects.select_related('user').filter(id=payment_id).afirst()
    
    if not payment:
        return await callback.answer("❌ To'lov topilmadi!", show_alert=True)
    
    # Delete the admin message
    global xabar
    if xabar:
        try:
            await xabar.delete()
        except:
            pass
    
    # Update payment status
    payment.status = 'REJECTED'
    await payment.asave(update_fields=['status'])
    
    # Send rejection to user
    try:
        await callback.bot.send_message(
            chat_id=payment.user.telegram_id,
            text="❌ Sizning referral to'lovingiz rad etildi. Iltimos, to'lovni tekshirib qayta urinib ko'ring."
        )
    except Exception as e:
        print(f"Error sending rejection: {e}")
    
    await callback.answer("❌ Referral to'lovi rad etildi!", show_alert=True)