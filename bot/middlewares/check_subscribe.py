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
        telegram_channels = [ch for ch in channels if ch.is_telegram]
        other_channels = [ch for ch in channels if not ch.is_telegram]

        # 🔹 Avval Telegram kanallarini tekshiramiz
        for channel in telegram_channels:
            chat_identifier = None

            # Avval telegram_id bilan urinish
            if channel.telegram_id:
                chat_identifier = channel.telegram_id
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=chat_identifier,
                        user_id=user_id
                    )
                    if member.status in ["left", "kicked"]:
                        not_subscribed_channels.append(channel)
                    continue  # Muvaffaqiyatli bo'lsa, keyingi kanalga o'tamiz
                
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    logging.warning(f"Telegram ID {channel.telegram_id} bilan xatolik: {e}. Username bilan urinib ko'ramiz.")
                except Exception as e:
                    logging.warning(f"Telegram ID bilan kutilmagan xatolik: {e}. Username bilan urinib ko'ramiz.")

            # Agar telegram_id ishlamasa yoki yo'q bo'lsa, username bilan urinish
            if channel.link and channel.link.startswith("https://t.me/"):
                username = channel.link.split("/")[-1]
                chat_identifier = "@" + username
                
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=chat_identifier,
                        user_id=user_id
                    )
                    if member.status in ["left", "kicked"]:
                        not_subscribed_channels.append(channel)
                    continue  # Muvaffaqiyatli bo'lsa, keyingi kanalga o'tamiz

                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    logging.error(f"Username @{username} bilan ham xatolik: {e}")
                except Exception as e:
                    logging.error(f"Username bilan kutilmagan xatolik: {e}")

            # Agar hech qanday identifikator ishlamasa
            if chat_identifier is None or not_subscribed_channels or len([ch for ch in not_subscribed_channels if ch.name == channel.name]) == 0:
                logging.error(f"Kanal {channel.name} uchun hech qanday to'g'ri identifikator topilmadi")
                not_subscribed_channels.append(channel)

        # 🔹 Agar foydalanuvchi hamma Telegram kanallariga a'zo bo'lsa
        if not not_subscribed_channels:
            # Telegram kanallarga a'zo ✅
            # Boshqa platformalar (YouTube, Instagram, ...) faqat tugma ko'rinadi, lekin bloklamaydi
            if other_channels:
                await self.send_subscription_message(message, other_channels, only_buttons=True)
            return await handler(event, data)

        # Agar hali Telegram kanallaridan chiqib ketgan bo'lsa → bloklash
        # Boshqa platformadagi kanallarni ham ko'rsatish (lekin bloklamaydi)
        await self.send_subscription_message(message, not_subscribed_channels + other_channels, block_user=True)
        return

    async def send_subscription_message(self, message: Message, channels: list, only_buttons: bool = False, block_user: bool = False):
        try:
            if block_user:
                base_message = getattr(
                    Messages.do_member_in_channel,
                    "value",
                    "📢 Botdan foydalanish uchun quyidagi majburiy kanallarga a'zo bo'ling:",
                )
            else:
                base_message = "🌐 Qo'shimcha homiy kanallar:"

            text = base_message + "\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])

            if channels:
                for channel in channels:
                    username = html.escape(channel.name or "Kanal")
                    link = getattr(channel, "link", None)

                    if channel.is_telegram:
                        button_text = f"📢 {username}"  # Telegram kanali
                    else:
                        button_text = f"🌐 {username}"  # Boshqa platforma

                    if link:
                        keyboard.inline_keyboard.append(
                            [InlineKeyboardButton(text=button_text, url=str(link))]
                        )
                        text += f"{button_text}\n"
                    else:
                        text += f"{button_text}\n"

            # Faqat bloklangan holatda "A'zolikni tekshirish" tugmasi ko'rinadi
            if block_user and not only_buttons:
                keyboard.inline_keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="✅ A'zolikni tekshirish",
                            callback_data="check_subscription",
                        )
                    ]
                )
                text += "\n💡 <b>Majburiy kanallarga a'zo bo'lgandan so'ng 'A'zolikni tekshirish' tugmasini bosing!</b>"

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