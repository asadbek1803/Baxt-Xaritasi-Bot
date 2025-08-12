import os
from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ContentType
from django.conf import settings
from aiogram.types import ReplyKeyboardRemove
from bot.models import Payments, Kurslar, TelegramUser
from bot.selectors import (
    get_kurs_details, 
    handle_user_level_advancement_workflow,
    check_and_handle_referrer_level_advancement
)
from bot.services.notification import send_message_to_all_admins
from bot.constants import Messages
from bot.states import BuyCourseState
from aiogram.fsm.state import State, StatesGroup
import asyncio

router = Router()
# State for buying course
class BuyCourseState(StatesGroup):
    WAITING_FOR_SCREENSHOT = State()



# To'lov rekvizitlari handleri
@router.callback_query(F.data.startswith("buy_course_"))
async def buy_course(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
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

    # Kurs ID ni saqlab qo'yamiz
    await state.update_data(course_id=course.id)
    await state.set_state(BuyCourseState.WAITING_FOR_SCREENSHOT)


# To'lov skrinshotini qabul qilish
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

    # To'lov yozuvini yaratish
    payment = await Payments.objects.acreate(
        user=user,
        course=course,
        amount=course.price,
        payment_type='COURSE',
        status='PENDING',
        payment_screenshot=screenshot_path
    )

    await message.answer(
        "✅ To'lov qabul qilindi! Adminlar tekshirgach, sizga xabar beramiz.", 
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
    # *** YANGI QO'SHILDI: To'lov qabul qilingandan so'ng referrer darajasini tekshirish ***
    await check_referrer_level_after_purchase(user_id, course.name)

    

async def check_referrer_level_after_purchase(user_telegram_id: str, course_name: str):
    """
    Kurs sotib olingandan keyin referrer darajasini tekshirish va kerakli harakatlarni bajarish
    """
    try:
        print(f"Checking referrer level for user {user_telegram_id} after purchasing {course_name}")
        
        # Referrer darajasini tekshirish
        check_result = await handle_user_level_advancement_workflow(user_telegram_id)
        
        if check_result['needs_replacement']:
            print(f"User {user_telegram_id} needs referrer replacement!")
            print(f"Message: {check_result['message']}")
            
            # Bu yerda adminlarga xabar yuborish yoki log yozish mumkin
            await notify_admin_about_referrer_issue(check_result)
        else:
            print(f"User {user_telegram_id} referrer level is OK: {check_result['message']}")
            
    except Exception as e:
        print(f"Error checking referrer level after purchase: {e}")


async def notify_admin_about_referrer_issue(check_result: dict):
    """
    Admin(lar)ga referrer muammosi haqida xabar yuborish
    """
    try:
        if not check_result['needs_replacement']:
            return
            
        user_data = check_result['user_data']
        referrer_data = check_result['current_referrer']
        
        admin_message = f"""
            🚨 <b>REFERRER DARAJASI MUAMMOSI</b>

            👤 <b>Foydalanuvchi:</b> {user_data['full_name']}
            📊 <b>Daraja:</b> {user_data['level']}
            🆔 <b>Telegram ID:</b> {user_data['telegram_id']}

            👥 <b>Hozirgi Referrer:</b> {referrer_data['full_name']}
            📊 <b>Referrer darajasi:</b> {referrer_data['level']}
            🆔 <b>Referrer ID:</b> {referrer_data['telegram_id']}

            ⚠️ <b>Muammo:</b> Foydalanuvchi darajasi referrer darajasidan yuqori!

            📨 <b>Ogohlantirish:</b> {'Yuborildi' if check_result['notification_sent'] else 'Yuborilmadi'}

            Iltimos, bu foydalanuvchi uchun yangi referrer tayinlang yoki mavjud referrerni darajasini oshiring.
        """
        
       
        await send_message_to_all_admins(admin_message)
        print("Admin notification would be sent:")
        print(admin_message)
        
    except Exception as e:
        print(f"Error notifying admin about referrer issue: {e}")


# Qo'shimcha: Admin uchun referrer almashtirish handler (ixtiyoriy)
@router.callback_query(F.data.startswith("replace_referrer_"))
async def admin_replace_referrer(callback: types.CallbackQuery):
    """
    Admin tomonidan referrerni almashtirish (qo'shimcha funksiya)
    """
    
    
    try:
        # Callback data formatı: replace_referrer_USER_ID_NEW_REFERRER_ID
        parts = callback.data.split("_")
        user_id = parts[2]
        new_referrer_id = parts[3]
        admin_id = str(callback.from_user.id)
        
        from bot.selectors import complete_referrer_replacement_workflow
        
        result = await complete_referrer_replacement_workflow(
            user_id, new_referrer_id, admin_id
        )
        
        if result['replacement_success']:
            await callback.message.answer(
                f"✅ Referrer muvaffaqiyatli almashtirildi!\n\n{result['message']}"
            )
        else:
            await callback.message.answer(
                f"❌ Referrer almashtirish xatosi:\n{result['message']}"
            )
            
    except Exception as e:
        await callback.message.answer(f"❌ Xatolik yuz berdi: {str(e)}")



# Screenshot saqlash funksiyasi (o'zgarishlarsiz)
async def save_payment_screenshot(bot: Bot, photo: types.PhotoSize, user_id: str) -> str:
    file = await bot.get_file(photo.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"course_payment_{user_id}_{timestamp}.jpg"

    save_dir = os.path.join(settings.MEDIA_ROOT, 'payment_screenshots')
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, file_name)
    await bot.download_file(file.file_path, destination=save_path)

    # DB ga nisbiy yo'lni qaytaramiz
    return os.path.join('payment_screenshots', file_name)