from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_contact(text: str):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=text, request_contact=True),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=1,
    )
    return keyboard
