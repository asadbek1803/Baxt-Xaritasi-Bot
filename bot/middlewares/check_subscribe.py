import logging
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.fsm.context import FSMContext
from bot.selectors import get_all_channels, get_all_admins, get_user
from bot.constants import Messages
from bot.states import UserRegistrationState
import html


class ChannelMembershipMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, skip_admins: bool = True):
        super().__init__()
        self.bot = bot
        self.skip_admins = skip_admins

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:

        user_id = event.from_user.id
        message = event.message if isinstance(event, CallbackQuery) else event

        # Registratsiya jarayonida yoki 'check_subscription' tugmasi bosilganda middleware'ni o'tkazib yuborish
        if isinstance(event, CallbackQuery) and event.data == "check_subscription":
            return await handler(event, data)

        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state in [
                UserRegistrationState.GET_FULL_NAME,
                UserRegistrationState.GET_PHONE_NUMBER,
                UserRegistrationState.GET_REGION,
                UserRegistrationState.GET_PROFESSION,
                UserRegistrationState.GET_GENDER,
            ]:
                return await handler(event, data)

        user = await get_user(str(user_id))
        if not user:
            return await handler(event, data)

        if self.skip_admins:
            try:
                admin_ids = await get_all_admins()
                if user_id in admin_ids:
                    return await handler(event, data)
            except Exception as e:
                logging.error(f"Admin tekshirishda xatolik: {e}")

        channels = await get_all_channels()
        if not channels:
            return await handler(event, data)

        not_subscribed_channels = []

        for channel in channels:
            is_telegram = getattr(channel, "is_telegram", True)

            if is_telegram and getattr(channel, "telegram_id", None):
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=channel.telegram_id, user_id=user_id
                    )

                    # ⭐ Asosiy o'zgarish: restricted statusini ham a'zo deb hisoblaymiz
                    if member.status in ["left", "kicked"]:
                        not_subscribed_channels.append(channel)

                except TelegramBadRequest as e:
                    logging.error(f"Kanal {channel.name} tekshirishda xatolik: {e}")
                    not_subscribed_channels.append(channel)
                except TelegramForbiddenError:
                    logging.error(
                        f"Bot kanaldan chiqarib yuborilgan yoki unga kira olmaydi: {channel.name}"
                    )
                    not_subscribed_channels.append(channel)
                except Exception as e:
                    logging.error(f"Kutilmagan xatolik: {e}")
                    not_subscribed_channels.append(channel)
            else:
                not_subscribed_channels.append(channel)

        # Faqatgina a'zo bo'lmagan (left, kicked) kanallar bo'lsa, bloklaymiz
        if not not_subscribed_channels:
            return await handler(event, data)

        await self.send_subscription_message(message, not_subscribed_channels)
        return

    async def send_subscription_message(self, message: Message, channels: list):
        try:
            base_message = getattr(
                Messages.do_member_in_channel,
                "value",
                "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
            )

            text = base_message + "\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])

            if channels:
                for channel in channels:
                    username = html.escape(channel.name or "Kanal")
                    link = getattr(channel, "link", None)
                    is_private = getattr(channel, "is_private", False)

                    if link:
                        button_text = (
                            f"🔒 {username}" if is_private else f"📢 {username}"
                        )
                        keyboard.inline_keyboard.append(
                            [InlineKeyboardButton(text=button_text, url=str(link))]
                        )
                        text += f"📢 <b>{username}</b>\n"
                    else:
                        text += f"📢 <b>{username}</b>\n"

            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text="✅ A'zolikni tekshirish",
                        callback_data="check_subscription",
                    )
                ]
            )

            text += "\n💡 <b>A'zo bo'lgandan so'ng 'A'zolikni tekshirish' tugmasini bosing!</b>"

            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logging.error(f"Xabar yuborishda xatolik: {e}")
            await message.answer(
                "📢 Botdan foydalanish uchun majburiy kanallarga a'zo bo'ling!"
            )
