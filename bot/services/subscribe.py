import logging
from aiogram import types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard
from bot.selectors import get_user, get_all_channels, get_user_buy_course
from bot.services.registration import send_course_offer


async def check_channels_after_registration(message: types.Message, bot: Bot):
    """Ro‘yxatdan o‘tgach majburiy kanallarni tekshirish."""
    user_id = message.from_user.id
    channels = await get_all_channels()
    not_subscribed_channels = []

    if channels:
        for channel in channels:
            try:
                member = await bot.get_chat_member(
                    chat_id=channel.telegram_id, user_id=user_id
                )
                if member.status in ["left", "kicked"]:
                    not_subscribed_channels.append(channel)
            except Exception as e:
                logging.error(f"Kanal tekshirishda xatolik: {e}")
                not_subscribed_channels.append(channel)

    if not not_subscribed_channels:
        user = await get_user(user_id)
        if await get_user_buy_course(user_id):
            await message.answer(
                text=Messages.welcome_message.value.format(full_name=user.full_name),
                reply_markup=get_menu_keyboard(),
            )
            return
        await send_course_offer(message)
    else:
        await send_subscription_message_after_registration(
            message, not_subscribed_channels
        )


async def send_subscription_message_after_registration(
    message: types.Message, channels: list
):
    """A’zo bo‘lish kerak bo‘lgan kanallar ro‘yxatini yuborish."""
    text = "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo‘ling:\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for channel in channels:
        button_text = (
            f"📢 {channel.name}" if not channel.is_private else f"🔒 {channel.name}"
        )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=button_text, url=channel.link)]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="✅ A'zolikni tekshirish", callback_data="check_subscription"
            )
        ]
    )

    text += "\n💡 <b>A'zo bo‘lgandan so‘ng tekshirish tugmasini bosing!</b>"
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
