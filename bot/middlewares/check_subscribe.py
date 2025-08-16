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

        # Registratsiya jarayonida middleware'ni o'tkazib yuborish
        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state in [
                UserRegistrationState.GET_FULL_NAME,
                UserRegistrationState.GET_PHONE_NUMBER,
                UserRegistrationState.GET_REGION,
                UserRegistrationState.GET_PROFESSION,
                UserRegistrationState.GET_GENDER,
                UserRegistrationState.GET_AGE,
            ]:
                return await handler(event, data)

        # 'check_subscription' tugmasi bosilganda alohida ishlov berish
        if isinstance(event, CallbackQuery) and event.data in ["check_subscription", "check_subscription_middleware"]:
    
            return await handler(event, data)

        user = await get_user(str(user_id))
        if not user:
            # Foydalanuvchi bazada yo'q bo'lsa (registratsiya qilmagan), middleware'ni o'tkazib yuborish
            return await handler(event, data)

        # ✅ YANGI: Foydalanuvchi yangi registratsiya qilgan bo'lsa, middleware'ni o'tkazib yuborish
        # Agar user mavjud lekin subscription_checked False bo'lsa, demak yangi foydalanuvchi
        if hasattr(user, 'subscription_checked') and not user.subscription_checked:
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

        # 🔹 Faqat Telegram kanallarini tekshiramiz (majburiy a'zolik uchun)
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
                    # API xatoligi bo'lsa, kanalga a'zo emas deb hisoblaymiz
                    not_subscribed_channels.append(channel)
                except Exception as e:
                    logging.error(f"Username bilan kutilmagan xatolik: {e}")
                    not_subscribed_channels.append(channel)
            else:
                # Agar hech qanday identifikator yo'q bo'lsa
                logging.error(f"Kanal {channel.name} uchun hech qanday to'g'ri identifikator topilmadi")
                not_subscribed_channels.append(channel)

        # 🔹 Agar Telegram kanallaridan birortasiga a'zo bo'lmasa - foydalanuvchini bloklash
        if not_subscribed_channels:
            await self.send_subscription_message(message, not_subscribed_channels, other_channels)
            return  # Handler'ni to'xtatamiz

        # 🔹 Agar hamma Telegram kanallariga a'zo bo'lsa - handler'ni davom ettirish
        return await handler(event, data)

    async def send_subscription_message(
        self, 
        message: Message, 
        not_subscribed_telegram_channels: list,
        other_channels: list = None
    ):
        try:
            if other_channels is None:
                other_channels = []
                
            text = getattr(
                Messages.do_member_in_channel,
                "value",
                "📢 Botdan foydalanish uchun quyidagi majburiy kanallarga a'zo bo'ling:\n\n",
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            
            # Majburiy Telegram kanallarini ko'rsatamiz
            for channel in not_subscribed_telegram_channels:
                username = html.escape(channel.name or "Kanal")
                link = getattr(channel, "link", None)
                button_text = f"📢 {username}"
                
                if link:
                    keyboard.inline_keyboard.append(
                        [InlineKeyboardButton(text=button_text, url=str(link))]
                    )
                    text += f"{button_text}\n"
            
            # Qo'shimcha platformalar (agar mavjud bo'lsa)
            if other_channels:
                text += "\n🌐 Qo'shimcha homiy kanallar:\n"
                for channel in other_channels:
                    username = html.escape(channel.name or "Kanal")
                    link = getattr(channel, "link", None)
                    button_text = f"🌐 {username}"
                    
                    if link:
                        keyboard.inline_keyboard.append(
                            [InlineKeyboardButton(text=button_text, url=str(link))]
                        )
                        text += f"{button_text}\n"
            
            # Tekshirish tugmasini qo'shamiz
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