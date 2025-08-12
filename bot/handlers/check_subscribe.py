from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.markdown import hbold

from bot.selectors import (
    get_all_channels,
    get_user,
    get_user_level,
    get_level_kurs,
    get_user_buy_course
)
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard
import logging
from typing import List

router = Router()

async def check_user_subscriptions(bot: Bot, user_id: int, channels: List) -> List:
    """Check user subscriptions to all channels and return unsubscribed ones"""
    not_subscribed = []
    
    for channel in channels:
        if not getattr(channel, "telegram_id", None):
            not_subscribed.append(channel)
            continue

        try:
            member = await bot.get_chat_member(channel.telegram_id, user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel)
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logging.error(f"Bot can't operate in channel {channel.name}: {e}")
            not_subscribed.append(channel)
        except Exception as e:
            logging.error(f"Subscription check error: {e}")
            not_subscribed.append(channel)
    
    return not_subscribed

async def handle_new_user_flow(callback: CallbackQuery, user_id: int):
    """Handle flow for new users (level 0)"""
    user = await get_user(user_id)
    user_level = await get_user_level(telegram_id=user_id)
    
    if await get_user_buy_course(telegram_id=user_id):
        await callback.message.delete()  # Clear previous message
        return await callback.message.answer(
            text=Messages.welcome_message.value.format(full_name=hbold(user.full_name)),
            reply_markup=get_menu_keyboard()
        )
    
    course = await get_level_kurs(level=user_level)
    if not course:
        await callback.message.delete()
        return await callback.message.answer(
            text="⚠️ Hozircha sizga mos kurs topilmadi. Iltimos, keyinroq urinib ko'ring.",
            reply_markup=get_menu_keyboard()
        )
    
    text = (
        f"🎓 {hbold(course.name)}\n\n"
        f"{course.description}\n\n"
        f"💵 Narxi: {hbold(f'{course.price} so\'m')}"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Sotib olish",
                    callback_data=f"buy_course_{course.id}"
                ),
                InlineKeyboardButton(
                    text="📢 Referralimni yaratish",
                    callback_data=f"create_referral_{course.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 A'zolikni tekshirish",
                    callback_data="check_subscription"
                )
            ]
        ]
    )
    
    await callback.message.edit_text(
        text=text, 
        reply_markup=keyboard
    )

@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    
    # Show checking status
    checking_msg = await callback.message.answer("🔍 A'zolik holati tekshirilmoqda...")
    
    try:
        channels = await get_all_channels()
        if not channels:
            await checking_msg.delete()
            return await callback.message.answer(
                "ℹ️ Hozircha a'zo bo'lish uchun kanallar mavjud emas.",
                reply_markup=get_menu_keyboard()
            )
        
        not_subscribed = await check_user_subscriptions(bot, user_id, channels)
        
        if not_subscribed:
            channels_list = "\n".join(
                f"➖ {channel.name}" 
                for channel in not_subscribed 
                if channel.name
            )
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔄 A'zolikni tekshirish",
                            callback_data="check_subscription"
                        )
                    ]
                ]
            )
            
            await checking_msg.delete()
            await callback.message.answer(
                f"❗️ Quyidagi kanal(lar)ga a'zo bo'lishingiz kerak:\n\n"
                f"{channels_list}\n\n"
                f"A'zo bo'lgach, «🔄 A'zolikni tekshirish» tugmasini bosing.",
                reply_markup=keyboard
            )
        else:
            await checking_msg.delete()
            await handle_new_user_flow(callback, user_id)
            
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        await checking_msg.delete()
        await callback.message.answer(
            "⚠️ A'zolikni tekshirishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
            reply_markup=get_menu_keyboard()
        )