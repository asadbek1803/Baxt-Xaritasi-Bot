import os
from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ContentType
from django.conf import settings

from bot.models import Payments, Kurslar, TelegramUser
from bot.selectors import get_kurs_details
from bot.constants import Messages
from bot.states import BuyCourseState

router = Router()

# To‘lov rekvizitlari handleri
@router.callback_query(F.data.startswith("buy_course_"))
async def buy_course(callback: types.CallbackQuery, state: FSMContext):
    course_id = int(callback.data.split("_")[-1])
    course = await get_kurs_details(course_id)

    if not course:
        return await callback.answer("❌ Kurs topilmadi!", show_alert=True)

    # Rekvizitlar matnini Messages ichidan olish
    rekvizitlar = Messages.payment_details.value.format(
        card_number="8600 1234 5678 9012",
        owner_name="Baxtiyor X",
        amount=course.price
    )

    await callback.message.answer(rekvizitlar, parse_mode="HTML")

    # Kurs ID ni saqlab qo‘yamiz
    await state.update_data(course_id=course.id)
    await state.set_state(BuyCourseState.WAITING_FOR_SCREENSHOT)


# To‘lov skrinshotini qabul qilish
@router.message(BuyCourseState.WAITING_FOR_SCREENSHOT, F.photo)
async def process_payment(message: types.Message, state: FSMContext, bot: Bot):
    user_id = str(message.from_user.id)
    data = await state.get_data()

    # Foydalanuvchi va kursni olish
    user = await TelegramUser.objects.filter(telegram_id=user_id).afirst()
    course = await Kurslar.objects.filter(id=data.get("course_id")).afirst()

    if not (user and course):
        return await message.answer("❌ Foydalanuvchi yoki kurs topilmadi.")

    # Rasmni saqlash
    screenshot_path = await save_payment_screenshot(bot, message.photo[-1], user_id)

    # To‘lov yozuvini yaratish
    await Payments.objects.acreate(
        user=user,
        course=course,
        amount=course.price,
        payment_type='COURSE',
        status='PENDING',
        payment_screenshot=screenshot_path
    )

    await message.answer("✅ To‘lov qabul qilindi! Adminlar tekshirgach, sizga xabar beramiz.")
    await state.clear()


# Screenshot saqlash funksiyasi
async def save_payment_screenshot(bot: Bot, photo: types.PhotoSize, user_id: str) -> str:
    file = await bot.get_file(photo.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"course_payment_{user_id}_{timestamp}.jpg"

    save_dir = os.path.join(settings.MEDIA_ROOT, 'payment_screenshots')
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, file_name)
    await bot.download_file(file.file_path, destination=save_path)

    # DB ga nisbiy yo‘lni qaytaramiz
    return os.path.join('payment_screenshots', file_name)
