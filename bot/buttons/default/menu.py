from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Mening hisobim"),
            ],
            [
                KeyboardButton(text="📞 Aloqa"),
                KeyboardButton(text="⚡️ Bosqichlar"),
            ],
            [
                KeyboardButton(text="📑 Loyiha haqida"),
                KeyboardButton(text="👥 Mening jamoam"),
            ],
            [
                KeyboardButton(text="❓ Yordam"),
                KeyboardButton(text="🏆 Sovg'alar"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=2,
    )
    return keyboard
