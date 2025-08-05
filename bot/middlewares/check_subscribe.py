import logging
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from bot.selectors import get_all_channels, get_all_admins


class ChannelMembershipMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, skip_admins: bool = True):
        super().__init__()
        self.bot = bot
        self.skip_admins = skip_admins

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:

        # Event turiga qarab user_id va message olish
        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            message = event.message
            
            # ⭐ Agar bu "check_subscription" callback'i bo'lsa, middleware'ni o'tkazib yuborish
            if event.data == "check_subscription":
                return await handler(event, data)
                
        else:
            user_id = event.from_user.id
            message = event

        # 1️⃣ Admin tekshirish
        if self.skip_admins:
            try:
                admin_ids = await get_all_admins()
                if user_id in admin_ids:
                    return await handler(event, data)
            except Exception as e:
                logging.error(f"Admin tekshirishda xatolik: {e}")

        # 2️⃣ Majburiy kanallarni olish
        channels = await get_all_channels()

        if not channels:
            # Agar majburiy kanal yo'q bo'lsa → davom etish
            return await handler(event, data)

        # 3️⃣ A'zo bo'lmagan kanallar ro'yxati
        not_subscribed_channels = []

        for channel in channels:
            is_telegram = getattr(channel, "is_telegram", True)

            if is_telegram and getattr(channel, "telegram_id", None):
                # Telegram kanali → API orqali tekshirish
                try:
                    member = await self.bot.get_chat_member(
                        chat_id=channel.telegram_id,
                        user_id=user_id
                    )
                    if member.status in ['left', 'kicked']:
                        not_subscribed_channels.append(channel)
                except TelegramBadRequest as e:
                    logging.error(f"Kanal {channel.name} tekshirishda xatolik: {e}")
                    not_subscribed_channels.append(channel)
                except Exception as e:
                    logging.error(f"Kutilmagan xatolik: {e}")
                    not_subscribed_channels.append(channel)
            else:
                # Telegram emas (Instagram, YouTube va h.k.) → tekshirishsiz
                not_subscribed_channels.append(channel)

        # Agar barcha kanallarga a'zo bo'lsa → davom etish
        if not not_subscribed_channels:
            return await handler(event, data)

        # 4️⃣ A'zo bo'lmagan kanallar haqida xabar yuborish
        await self.send_subscription_message(message, not_subscribed_channels)
        return  # Handler'ni chaqirmaymiz

    async def send_subscription_message(self, message: Message, channels: list):
        """
        A'zo bo'lmagan kanallar haqida xabar yuborish
        """
        text = "🔒 <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz kerak:</b>\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        for channel in channels:
            username = channel.name or "Kanal"
            link = getattr(channel, "link", None)

            text += f"📢 <b>{username}</b>\n"

            if link:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"📢 {username}",
                        url=link
                    )
                ])

        # Tekshirish tugmasi
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="✅ A'zolikni tekshirish",
                callback_data="check_subscription"
            )
        ])

        text += "\n💡 <b>A'zo bo'lgandan so'ng \"A'zolikni tekshirish\" tugmasini bosing!</b>"

        try:
            await message.answer(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Xabar yuborishda xatolik: {e}")
            await message.answer(
                "🔒 Botdan foydalanish uchun majburiy kanallarga a'zo bo'lishingiz kerak!"
            )