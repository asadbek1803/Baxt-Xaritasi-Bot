# stages.py - Tuzatilgan handler

from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.selectors import (
    get_user,
    get_user_level,
    get_level_kurs,
    get_user_purchased_courses_with_levels,
)

router = Router()

def get_stages_keyboard(user_level: str, purchased_course_levels: set) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    
    # Foydalanuvchi bosqich raqamini to'g'ri olish
    try:
        if user_level.startswith('level_'):
            current_level = int(user_level.split('_')[1])
        elif "-bosqich" in user_level:
            current_level = int(user_level.split("-")[0])
        else:
            current_level = 0
    except:
        current_level = 0
        
    print(f"User current level: {current_level}")
    print(f"Purchased course levels: {purchased_course_levels}")
    
    # Eng yuqori sotib olingan levelni topish
    max_purchased_level = max(purchased_course_levels) if purchased_course_levels else 0
    
    print(f"Max purchased level: {max_purchased_level}")
    
    # 1 dan 7 gacha bosqichlar uchun tugmalar
    for level_num in range(1, 8):
        level_name = f"{level_num}-bosqich"
        
        # Kursni sotib olganmi?
        is_purchased = level_num in purchased_course_levels
        
        # Bu levelga kirish huquqi bormi?
        # Mantiq: sotib olingan levellar + keyingi bitta level ochiq
        can_access = level_num == max_purchased_level + 1
        print(can_access)
        print(f"Level {level_num}: purchased={is_purchased}, can_access={can_access}")
        
        if can_access == True:
            # Sotib olinmagan lekin ochiq
            button_text = f"🔓 {level_name}"
            callback_data = f"stage_available_{level_num}"
        elif is_purchased:
            # Sotib olingan kurs - doimo yashil
            button_text = f"✅ {level_name}"
            callback_data = f"stage_completed_{level_num}"
        else:
            # Qulflangan
            button_text = f"🔒 {level_name}"
            callback_data = f"stage_locked_{level_num}"

        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_home")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

@router.message(F.text == "⚡️ Bosqichlar")
async def show_stages(message: types.Message, state: FSMContext):
    """Bosqichlar haqida ma'lumot ko'rsatish"""
    user_id = str(message.from_user.id)

    # Foydalanuvchini olish
    user = await get_user(user_id)
    if not user:
        await message.answer(
            "❌ Foydalanuvchi topilmadi. Iltimos /start buyrug'ini bosing."
        )
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
🔓 - Ochiq bosqich (sotib olish mumkin)
🔒 - Yopiq bosqich (avval oldingi bosqichni tugating)

<b>Qoidalar:</b>
• Har bir bosqichni ketma-ket o'tishingiz kerak
• Keyingi bosqichga o'tish uchun kursni sotib olishingiz kerak
• Bosqichlarni saklab o'ta olmaysiz

<b>Sotib olingan kurslar:</b> {', '.join([f'{x}-bosqich' for x in sorted(purchased_course_levels)]) if purchased_course_levels else 'Hozircha yo\'q'}
    """

    keyboard = get_stages_keyboard(user_level, purchased_course_levels)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("stage_"))
async def handle_stage_callback(callback: types.CallbackQuery, state: FSMContext):
    """Bosqich tugmalarini boshqarish"""
    user_id = str(callback.from_user.id)
    action_data = callback.data.split("_")
    
    if len(action_data) < 3:
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return

    stage_type = action_data[1]
    level_num = int(action_data[2])
    level_name = f"{level_num}-bosqich"
    
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi")
        return

    if stage_type == "completed":
        await callback.answer(f"✅ {level_name} bosqichi tugallangan!", show_alert=True)

    elif stage_type == "available":
        # Bu level uchun kurs topish
        course = await get_level_kurs(level_name)

        if course:
            text = f"""
🎯 <b>{level_name} bosqichi</b>

Bu bosqichni tugallash uchun quyidagi kursni sotib olishingiz kerak:

📚 <b>{course.name}</b>
💰 Narxi: {course.price:,} so'm
📖 Ta'rif: {course.description}

Kursni sotib olishni xohlaysizmi?
            """

            keyboard_buttons = []
            
            # Agar user tasdiqlanmagan bo'lsa, referral opsiyasini ham ko'rsatish
            if not user.is_confirmed:
                text += "\n\n💡 <b>Referral yaratish orqali ham kurs olishingiz mumkin!</b>"
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="📢 Referral yaratish",
                        callback_data=f"create_referral_{course.id}"
                    )
                ])
            else:


                keyboard_buttons.extend([
                    [
                        InlineKeyboardButton(
                            text="💳 Sotib olish",
                            callback_data=f"buy_course_{course.id}"
                        )
                    ]])
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text="◀️ Orqaga", 
                        callback_data="back_to_stages"
                    )
                ]
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer(f"❌ {level_name} uchun kurs topilmadi", show_alert=True)

    elif stage_type == "locked":
        await callback.answer(
            f"🔒 {level_name} bosqichi hali yopiq!\n\n"
            f"Avval oldingi bosqichlarni tugating.",
            show_alert=True
        )


@router.callback_query(F.data == "back_to_stages")
async def back_to_stages(callback: types.CallbackQuery, state: FSMContext):
    """Bosqichlar menyusiga qaytish"""
    user_id = str(callback.from_user.id)
    

    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi")
        return

    user_level = await get_user_level(user_id)
    if not user_level:
        user_level = "0-bosqich"

    purchased_course_levels = await get_user_purchased_courses_with_levels(user_id)

    text = f"""
🎯 <b>Bosqichlar</b>

Sizning hozirgi darajangiz: <b>{user_level}</b>

<b>Bosqichlar haqida:</b>
✅ - Tugallangan bosqich (kurs sotib olingan)
🔓 - Ochiq bosqich (sotib olish mumkin)
🔒 - Yopiq bosqich (avval oldingi bosqichni tugating)

<b>Qoidalar:</b>
• Har bir bosqichni ketma-ket o'tishingiz kerak
• Keyingi bosqichga o'tish uchun kursni sotib olishingiz kerak
• Bosqichlarni saklab o'ta olmaysiz

<b>Sotib olingan kurslar:</b> {', '.join([f'{x}-bosqich' for x in sorted(purchased_course_levels)]) if purchased_course_levels else 'Hozircha yo\'q'}
    """

    keyboard = get_stages_keyboard(user_level, purchased_course_levels)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")