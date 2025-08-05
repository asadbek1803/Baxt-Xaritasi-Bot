from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery

from bot.selectors import get_all_channels
import logging

router = Router()

@router.callback_query(lambda c: c.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    """
    A'zolikni tekshirish tugmasi
    """
    user_id = callback.from_user.id
    channels = await get_all_channels()

    not_subscribed_channels = []

    for channel in channels:
        is_telegram = getattr(channel, "is_telegram", True)
        
        if is_telegram and getattr(channel, "telegram_id", None):
            try:
                member = await bot.get_chat_member(
                    chat_id=channel.telegram_id,
                    user_id=user_id
                )
                if member.status in ['left', 'kicked']:
                    not_subscribed_channels.append(channel)
            except Exception as e:
                logging.error(f"A'zolik tekshirishda xatolik: {e}")
                not_subscribed_channels.append(channel)
        else:
            # Telegram emas platformalar → tekshirishsiz, ammo ro'yxatda qoladi
            not_subscribed_channels.append(channel)

    if not not_subscribed_channels:
        await callback.answer("✅ Tabriklaymiz! Siz barcha kanallarga a'zo bo'lgansiz!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception as e:
            logging.error(f"Xabarni o'chirishda xatolik: {e}")
    else:
        await callback.answer("❌ Siz hali ham barcha kanallarga a'zo bo'lmagansiz!", show_alert=True)