import logging
from typing import List, Optional
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.markdown import hbold
from aiogram.fsm.context import FSMContext

from bot.handlers.registration import verify_and_show_content
from bot.selectors import (
    get_all_channels,
    get_user,
    get_user_level,
    get_level_kurs,
    get_user_buy_course,
    get_all_admins
)
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard
import html

router = Router()


async def check_user_subscriptions(bot: Bot, user_id: int, channels: List) -> List:
    """Check user subscriptions with same logic as middleware"""
    not_subscribed = []
    telegram_channels = [ch for ch in channels if ch.is_telegram]
    for channel in telegram_channels:
        chat_identifier = None

        if channel.telegram_id:
            chat_identifier = channel.telegram_id
            try:
                member = await bot.get_chat_member(
                    chat_id=chat_identifier,
                    user_id=user_id
                )
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel)
                continue

            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logging.warning(f"Telegram ID {channel.telegram_id} bilan xatolik: {e}. Username bilan urinib ko'ramiz.")
            except Exception as e:
                logging.warning(f"Unexpected error with telegram_id: {e}")

        # Fallback to username from link
        if channel.link and channel.link.startswith("https://t.me/"):
            username = channel.link.split("/")[-1]
            chat_identifier = "@" + username

            try:
                member = await bot.get_chat_member(
                    chat_id=chat_identifier,
                    user_id=user_id
                )
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel)
            except (TelegramBadRequest, TelegramForbiddenError):
                not_subscribed.append(channel)
            except Exception as e:
                logging.error(f"Error checking channel {channel.name}: {e}")
                not_subscribed.append(channel)
        else:
            not_subscribed.append(channel)

    return not_subscribed


async def handle_verified_user(message: Message, user_id: int):
    """Handle post-verification flow consistent with middleware"""
    try:
        # Skip check for admins (same as middleware)
        admin_ids = await get_all_admins()
        if user_id in admin_ids:
            return await show_user_content(message, user_id)

        user = await get_user(user_id)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi!")
            return

        # Check purchased courses first
        if await get_user_buy_course(telegram_id=user_id):
            await message.answer(
                text=Messages.welcome_message.value.format(full_name=hbold(user.full_name)),
                reply_markup=get_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        # Show course based on level
        await show_level_content(message, user_id)

    except Exception as e:
        logging.error(f"Verified user flow error: {e}")
        await message.answer(Messages.system_error.value)


async def show_user_content(message: Message, user_id: int):
    """Show appropriate content for verified user"""
    try:
        user = await get_user(user_id)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi!")
            return

        if await get_user_buy_course(telegram_id=user_id):
            await message.answer(
                text=Messages.welcome_message.value.format(full_name=hbold(user.full_name)),
                reply_markup=get_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await show_level_content(message, user_id)
    except Exception as e:
        logging.error(f"Error showing user content: {e}")
        await message.answer(Messages.system_error.value)


async def show_level_content(message: Message, user_id: int):
    """Show content based on user level"""
    user_level = await get_user_level(telegram_id=user_id)
    course = await get_level_kurs(level=user_level)
    
    if not course:
        await message.answer(
            "⚠️ Sizning levelingizga mos kurs hozircha mavjud emas.",
            reply_markup=get_menu_keyboard(),
        )
        return

    text = (
        f"🎓 <b> {course.name} </b> \n\n"
        f"{course.description}\n\n"
        f"💵 Narxi: <b> {course.price} </b> so\'m'"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buy_course_{course.id}")]
        ]
    )

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


async def show_subscription_request(
    message: Message, 
    not_subscribed_channels: List,
    other_channels: List = None,
    referral_message: str = ""
):
    """Show subscription request matching middleware format"""
    if other_channels is None:
        other_channels = []

    try:
        text = "🎉 Registratsiya muvaffaqiyatli yakunlandi!" + referral_message
        text += "\n\n📢 Botdan to'liq foydalanish uchun quyidagi majburiy kanallarga a'zo bo'ling:\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        # Required channels
        for channel in not_subscribed_channels:
            name = html.escape(channel.name or "Kanal")
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=f"📢 {name}", url=channel.link)]
            )
            text += f"📢 {name}\n"

        # Additional channels
        if other_channels:
            text += "\n🌐 Qo'shimcha homiy kanallar:\n"
            for channel in other_channels:
                name = html.escape(channel.name or "Kanal")
                keyboard.inline_keyboard.append(
                    [InlineKeyboardButton(text=f"🌐 {name}", url=channel.link)]
                )
                text += f"🌐 {name}\n"

        # Verification button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="✅ A'zolikni tekshirish",
                callback_data="check_subscription"
            )
        ])

        text += "\n💡 <b>Majburiy kanallarga a'zo bo'lgandan so'ng tekshirish tugmasini bosing!</b>"

        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Subscription message error: {e}")
        await message.answer("📢 Iltimos, barcha kanallarga a'zo bo'ling!")


@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Handle subscription check with same logic as middleware"""
    user_id = callback.from_user.id

    try:
        channels = await get_all_channels()
        if not channels:
            await callback.answer("✅ Majburiy kanallar mavjud emas")
            return await handle_verified_user(callback.message, user_id)

        # Separate channel types like middleware
        telegram_channels = [ch for ch in channels if ch.is_telegram]
        not_subscribed = await check_user_subscriptions(bot, user_id, telegram_channels)

        if not_subscribed:
            channel_names = "\n".join([f"• {ch.name}" for ch in not_subscribed])
            await callback.answer(
                f"❌ Quyidagi kanallarga a'zo bo'lmagansiz:\n{channel_names}",
                show_alert=True
            )
        else:
            await callback.answer("✅ A'zolik tasdiqlandi!")
            await callback.message.delete()
            await verify_and_show_content(callback.message, user_id)

    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        await callback.answer("⚠️ Tekshirishda xatolik yuz berdi!", show_alert=True)


async def force_subscription_check(message: Message, bot: Bot) -> bool:
    """Force check matching middleware logic"""
    try:
        channels = await get_all_channels()
        if not channels:
            return True

        telegram_channels = [ch for ch in channels if ch.is_telegram]
        other_channels = [ch for ch in channels if not ch.is_telegram]

        not_subscribed = await check_user_subscriptions(bot, message.from_user.id, telegram_channels)

        if not_subscribed:
            await show_subscription_request(
                message,
                not_subscribed_channels=not_subscribed,
                other_channels=other_channels
            )
            return False

        return True
    except Exception as e:
        logging.error(f"Force check error: {e}")
        return False
