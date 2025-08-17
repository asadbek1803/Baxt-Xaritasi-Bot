from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Mening hisobim"),
                KeyboardButton(text="🔗 Mening havolam"),
            ],
            [
                KeyboardButton(text="👥 Mening jamoam"),
                KeyboardButton(text="⚡️ Bosqichlar"),
            ],
            [
                KeyboardButton(text="📑 Loyiha haqida"),
                KeyboardButton(text="🏆 Sovg'alar"),
            ],
            [
                KeyboardButton(text="📞 Aloqa"),
                KeyboardButton(text="❓ Yordam"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=2,
    )
    return keyboard
