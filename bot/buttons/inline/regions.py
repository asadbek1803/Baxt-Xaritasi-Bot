from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.constants import REGIONS


def get_region_buttons() -> InlineKeyboardMarkup:
    """
    Generate inline keyboard buttons for region selection based on the
    provided language code.

    :param language_code: Language code to determine button labels.
    :return: InlineKeyboardMarkup with region buttons.
    """
    buttons = [
        InlineKeyboardButton(text=region[1], callback_data=f"region_{region[0]}")
        for region in REGIONS
    ]
    # Arrange buttons in rows of two
    keyboard = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    keyboard.append(
        [InlineKeyboardButton(text="Boshqa/Другие", callback_data="other_region")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
