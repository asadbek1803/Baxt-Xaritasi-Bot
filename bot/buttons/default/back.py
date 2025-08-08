from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_back_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 Orqaga"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=1,
    )
    return keyboard