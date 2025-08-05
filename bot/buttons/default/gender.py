from bot.constants import GENDER
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_gender_keyboard():
    """Jins klaviaturasi"""
    keyboard = [
        [KeyboardButton(text="Erkak"), KeyboardButton(text="Ayol")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
