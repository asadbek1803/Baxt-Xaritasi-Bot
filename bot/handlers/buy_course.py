import os
from aiogram import types, F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.selectors import get_kurs_details
from bot.models import Payments, Kurslar, TelegramUser
from bot.constants import Messages
from django.conf import settings
from datetime import datetime
from bot.states import UserRegistrationState
from bot.buttons.default.back import get_back_keyboard
from aiogram.enums import ContentType

router = Router()

class BuyCourseState(StatesGroup):
    WAITING_FOR_SCREENSHOT = State()
    COURSE_ID = State()

@router.callback_query(F.data.startswith("buy_course_"))
async def buy_latest_course(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    course_id = callback.data.split("_")[-1]
    course = await get_kurs_details(int(course_id))
    if not course:
        await callback.answer("Kurs topilmadi!", show_alert=True)
        return

    # Rekvizitlarni chiqarish
    rekvizitlar = (
        f"💳 <b>To'lov uchun rekvizitlar:</b>\n"
        f"🏦 Karta raqami: <code>8600 1234 5678 9012</code>\n"
        f"Ism: Baxtiyor X\n\n"
        f"To'lov summasi: <b>{course.price} so'm</b>\n\n"
        f"To'lovni amalga oshirib, chek (screenshot) yuboring."
    )
    await callback.message.answer(
        text=rekvizitlar,
        parse_mode="HTML"
    )
    await state.update_data(course_id=course.id)
    await state.set_state(BuyCourseState.WAITING_FOR_SCREENSHOT)

@router.message(BuyCourseState.WAITING_FOR_SCREENSHOT, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext, bot: Bot):
    # Foydalanuvchi va kurs ma'lumotlarini olish
    user_id = str(message.from_user.id)
    user = await TelegramUser.objects.filter(telegram_id=user_id).afirst()
    data = await state.get_data()
    course_id = data.get("course_id")

    if not user or not course_id:
        await message.answer("Xatolik! Foydalanuvchi yoki kurs topilmadi.")
        return

    course = await Kurslar.objects.filter(id=course_id).afirst()
    if not course:
        await message.answer("Kurs topilmadi.")
        return

    # Rasmni yuklab olish va saqlash
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    # Fayl nomini yaratish (user_id + timestamp)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"course_payment_{user_id}_{timestamp}.jpg"
    
    # MEDIA_ROOT ga saqlash
    save_path = os.path.join(settings.MEDIA_ROOT, 'payment_screenshots', file_name)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Faylni yuklab olish
    await bot.download_file(file.file_path, destination=save_path)

    # To'lovni yaratish
    payment = await Payments.objects.acreate(
        user=user,
        course=course,
        amount=course.price,
        payment_type='COURSE',
        status='PENDING',
        payment_screenshot=os.path.join('payment_screenshots', file_name)  # DB ga nisbiy yo'l saqlanadi
    )

    await message.answer(
        "✅ To'lov skrinshoti qabul qilindi! Adminlar tomonidan tekshirilgach, sizga xabar beriladi."
    )
    await state.clear()