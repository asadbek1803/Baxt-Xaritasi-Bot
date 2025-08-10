from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.buttons.default.menu import get_menu_keyboard
from bot.selectors import (
    get_user,
    get_user_level,
    get_user_active_payments,
    get_level_kurs,
    LEVEL_MAPPING,
    REVERSE_LEVEL_MAPPING,
    get_user_purchased_courses_with_levels
)

router = Router()
global msg

def get_stages_keyboard(user_level: str, purchased_course_levels: set) -> InlineKeyboardMarkup:
    """
    Foydalanuvchi leveliga va sotib olgan kurslar levellariga qarab bosqichlar klaviaturasini yaratish
    """
    keyboard_buttons = []

    # Foydalanuvchining hozirgi level raqamini olish
    try:
        current_level_num = int(user_level.split('-')[0])
    except (ValueError, AttributeError):
        current_level_num = 0

    # 7 ta bosqich uchun tugmalar yaratish
    for level_num in range(1, 8):  # 1 dan 7 gacha
        level_name = f"{level_num}-bosqich"

        # Tugma matni va holatini aniqlash
        if level_num in purchased_course_levels:
            button_text = f"✅ {level_name}"
            callback_data = f"stage_completed_{level_num}"
        elif level_num <= current_level_num:
            button_text = f"🔓 {level_name}"
            callback_data = f"stage_available_{level_num}"
        elif level_num == current_level_num + 1:
            button_text = f"🔐 {level_name}"
            callback_data = f"stage_next_{level_num}"
        else:
            button_text = f"🔒 {level_name}"
            callback_data = f"stage_locked_{level_num}"

        # Tugma qo'shish
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=callback_data
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(
            text="◀️ Orqaga",
            callback_data="back_to_home"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


@router.message(F.text == "⚡️ Bosqichlar")
async def show_stages(message: types.Message, state: FSMContext):
    """
    Bosqichlar haqida ma'lumot ko'rsatish
    """
    user_id = str(message.from_user.id)
    
    # Foydalanuvchini olish
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Iltimos /start buyrug'ini bosing.")
        return
    
    # Foydalanuvchi levelini olish
    user_level = await get_user_level(user_id)
    if not user_level:
        user_level = "0-bosqich"  # Default level
    
    # Foydalanuvchi sotib olgan kurslar levellarini olish
    purchased_course_levels = await get_user_purchased_courses_with_levels(user_id)
    
    # Bosqichlar haqida matn
    text = f"""
🎯 <b>Bosqichlar</b>

Sizning hozirgi darajangiz: <b>{user_level}</b>

<b>Bosqichlar haqida:</b>
✅ - Tugallangan bosqich (kurs sotib olingan)
🔓 - Ochiq bosqich (kurs sotib olinmagan)
🔐 - Keyingi bosqich (sotib olish mumkin)
🔒 - Yopiq bosqich (avval oldingi bosqichni tugating)

<b>Qoidalar:</b>
• Har bir bosqichni ketma-ket o'tishingiz kerak
• Keyingi bosqichga o'tish uchun oldingi bosqichdagi kursni sotib olishingiz kerak
• Bosqichlarni saklab o'ta olmaysiz
    """
    
    keyboard = get_stages_keyboard(user_level, purchased_course_levels)
    
    msg = await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("stage_"))
async def handle_stage_callback(callback: types.CallbackQuery, state: FSMContext):
    """
    Bosqich tugmalarini boshqarish
    """
    user_id = str(callback.from_user.id)
    action_data = callback.data.split("_")
    
    if len(action_data) < 3:
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    
    stage_type = action_data[1]  # completed, available, next, locked
    level_num = int(action_data[2])
    level_name = f"{level_num}-bosqich"
    
    if stage_type == "completed":
        # Tugallangan bosqich - ma'lumot ko'rsatish
        await callback.answer(f"✅ {level_name} bosqichi tugallangan!", show_alert=True)
        
    elif stage_type == "available":
        # Ochiq bosqich (lekin kurs sotib olinmagan) - kurs sotib olishni taklif qilish
        previous_level = f"{level_num-1}-bosqich"
        course = await get_level_kurs(previous_level)
        
        if course:
            text = f"""
🎯 <b>{level_name} bosqichi</b>

Bu bosqichni tugallash uchun quyidagi kursni sotib olishingiz kerak:

📚 <b>{course.name}</b>
💰 Narxi: {course.price:,} so'm
📖 Ta'rif: {course.description}

Kursni sotib olishni xohlaysizmi?
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Sotib olish",
                        callback_data=f"buy_course_{course.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Orqaga",
                        callback_data="back_to_stages"
                    )
                ]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.answer(
                f"❌ {level_name} uchun kurs topilmadi",
                show_alert=True
            )
        
    elif stage_type == "next":
        # Keyingi bosqich - kurs sotib olishni taklif qilish
        previous_level = f"{level_num-1}-bosqich"
        course = await get_level_kurs(previous_level)
        
        if course:
            text = f"""
🎯 <b>{level_name} bosqichi</b>

Bu bosqichga o'tish uchun quyidagi kursni sotib olishingiz kerak:

📚 <b>{course.name}</b>
💰 Narxi: {course.price:,} so'm
📖 Ta'rif: {course.description}

Kursni sotib olishni xohlaysizmi?
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Sotib olish",
                        callback_data=f"buy_course_{course.id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Orqaga",
                        callback_data="back_to_stages"
                    )
                ]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.answer(
                f"❌ {level_name} uchun kurs topilmadi",
                show_alert=True
            )
    
    elif stage_type == "locked":
        # Yopiq bosqich - ogohlantirish
        await callback.answer(
            f"🔒 {level_name} bosqichi hali yopiq!\n\n"
            f"Avval oldingi bosqichlarni tugating.",
            show_alert=True
        )

@router.callback_query(F.data == "back_to_stages")
async def back_to_stages(callback: types.CallbackQuery, state: FSMContext):
    """
    Bosqichlar menyusiga qaytish
    """
    user_id = str(callback.from_user.id)
    
    # Foydalanuvchini olish
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi")
        return
    
    # Foydalanuvchi levelini olish
    user_level = await get_user_level(user_id)
    if not user_level:
        user_level = "0-bosqich"
    
    # Foydalanuvchi sotib olgan kurslar levellarini olish
    purchased_course_levels = await get_user_purchased_courses_with_levels(user_id)
    
    # Bosqichlar haqida matn
    text = f"""
🎯 <b>Bosqichlar</b>

Sizning hozirgi darajangiz: <b>{user_level}</b>

<b>Bosqichlar haqida:</b>
✅ - Tugallangan bosqich (kurs sotib olingan)
🔓 - Ochiq bosqich (kurs sotib olinmagan)
🔐 - Keyingi bosqich (sotib olish mumkin)
🔒 - Yopiq bosqich (avval oldingi bosqichni tugating)

<b>Qoidalar:</b>
• Har bir bosqichni ketma-ket o'tishingiz kerak
• Keyingi bosqichga o'tish uchun oldingi bosqichdagi kursni sotib olishingiz kerak
• Bosqichlarni saklab o'ta olmaysiz
    """
    
    keyboard = get_stages_keyboard(user_level, purchased_course_levels)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )



