from bot.constants import PROFESSIONS
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_profession_buttons() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"profession_{code}")
        for code, name in PROFESSIONS
    ]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



