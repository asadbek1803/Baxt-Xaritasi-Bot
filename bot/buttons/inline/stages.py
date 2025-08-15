from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_stages_keyboard(
    user_level: str, purchased_course_levels: set, add_back_button: bool = True
) -> InlineKeyboardMarkup:
    """
    Foydalanuvchi leveliga va sotib olgan kurslar levellariga qarab bosqichlar klaviaturasini yaratish
    """
    keyboard_buttons = []

    # Foydalanuvchining hozirgi level raqamini olish
    try:
        current_level_num = int(user_level.split("-")[0])
    except (ValueError, AttributeError):
        current_level_num = 0

    # 7 ta bosqich uchun tugmalar yaratish
    current_level_num += 1
    for level_num in range(1, 8):  # 1 dan 7 gacha
        level_name = f"{level_num}-bosqich"

        # Tugma matni va holatini aniqlash
        if level_num in purchased_course_levels:
            button_text = f"✅ {level_name}"
            callback_data = f"stage_completed_{level_num}"
        elif level_num <= current_level_num:
            button_text = f"🔓 {level_name}"
            callback_data = f"stage_available_{level_num}"
        else:
            button_text = f"🔒 {level_name}"
            callback_data = f"stage_locked_{level_num}"

        # Tugma qo'shish
        keyboard_buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        )

    if add_back_button:
        keyboard_buttons.append(
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_home")]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
