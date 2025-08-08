from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_age_button() -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with age options.
    """
    age_options = [
        ("18-24", "age_18_24"),
        ("25-34", "age_25_34"),
        ("35-44", "age_35_44"),
        ("45+", "age_45_plus")
    ]
    
    # Yangi usul: avval tugmalar ro'yxatini yaratamiz
    buttons = [
        InlineKeyboardButton(text=label, callback_data=callback_data)
        for label, callback_data in age_options
    ]
    
    # Keyin InlineKeyboardMarkup yaratamiz
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        buttons[:2],  # Birinchi qator (2 ta tugma)
        buttons[2:]   # Ikkinchi qator (qolgan 2 ta tugma)
    ])
    
    return keyboard