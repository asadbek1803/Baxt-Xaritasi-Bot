import logging
from typing import List

from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.markdown import hbold

from bot.selectors import (
    get_all_channels,
    get_user,
    get_user_level,
    get_level_kurs,
    get_user_buy_course,
)
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard

router = Router()


async def check_user_subscriptions(bot: Bot, user_id: int, channels: List) -> List:
    """Foydalanuvchi barcha Telegram kanallarga obuna bo'lganligini tekshiradi va obuna bo'lmaganlarini qaytaradi"""
    not_subscribed = []

    # Faqat Telegram kanallarini tekshiramiz
    telegram_channels = [ch for ch in channels if ch.is_telegram]
    
    for channel in telegram_channels:
        chat_identifier = None
        channel_found = False

        # Avval telegram_id bilan urinish
        if channel.telegram_id:
            chat_identifier = channel.telegram_id
            try:
                member = await bot.get_chat_member(
                    chat_id=chat_identifier,
                    user_id=user_id
                )
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel)
                channel_found = True
                continue  # Muvaffaqiyatli bo'lsa, keyingi kanalga o'tamiz
                
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logging.warning(f"Telegram ID {channel.telegram_id} bilan xatolik: {e}. Username bilan urinib ko'ramiz.")
            except Exception as e:
                logging.warning(f"Telegram ID bilan kutilmagan xatolik: {e}. Username bilan urinib ko'ramiz.")

        # Agar telegram_id ishlamasa yoki yo'q bo'lsa, username bilan urinish
        if not channel_found and channel.link and channel.link.startswith("https://t.me/"):
            username = channel.link.split("/")[-1]
            chat_identifier = "@" + username
            
            try:
                member = await bot.get_chat_member(
                    chat_id=chat_identifier,
                    user_id=user_id
                )
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel)
                channel_found = True
                continue  # Muvaffaqiyatli bo'lsa, keyingi kanalga o'tamiz

            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logging.error(f"Username @{username} bilan ham xatolik: {e}")
                # API xatoligi bo'lsa, a'zo emas deb hisoblaymiz
                not_subscribed.append(channel)
                channel_found = True
            except Exception as e:
                logging.error(f"Username bilan kutilmagan xatolik: {e}")
                not_subscribed.append(channel)
                channel_found = True

        # Agar hech qanday identifikator yo'q bo'lsa
        if not channel_found:
            logging.error(f"Kanal {channel.name} uchun hech qanday to'g'ri identifikator topilmadi")
            not_subscribed.append(channel)

    return not_subscribed


async def handle_new_user_flow(callback: CallbackQuery, user_id: int):
    """
    Foydalanuvchini leveliga qarab kurs chiqaradi.
    Agar foydalanuvchi kurs sotib olgan bo'lsa, menyuga yuboradi.
    """
    user = await get_user(user_id)
    user_level = await get_user_level(telegram_id=user_id)

    # Agar foydalanuvchi allaqachon kurs sotib olgan bo'lsa
    if await get_user_buy_course(telegram_id=user_id):
        await callback.message.delete()
        return await callback.message.answer(
            text=Messages.welcome_message.value.format(full_name=hbold(user.full_name)),
            reply_markup=get_menu_keyboard(),
            parse_mode="HTML"
        )

    # Level bo'yicha kursni olish
    course = await get_level_kurs(level=user_level)
    if not course:
        await callback.message.delete()
        return await callback.message.answer(
            text="⚠️ Sizning levelingizga mos kurs hozircha mavjud emas. Keyinroq urinib ko'ring.",
            reply_markup=get_menu_keyboard(),
        )

    # Kurs haqida ma'lumot chiqarish
    text = (
        f"🎓 {hbold(course.name)}\n\n"
        f"{course.description}\n\n"
        f"💵 Narxi: {hbold(f'{course.price} so\'m')}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Sotib olish", callback_data=f"buy_course_{course.id}"
                )
            ],
        ]
    )

    await callback.message.edit_text(text=text, reply_markup=keyboard)


@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    """
    Foydalanuvchi kanallarni tekshiradi.
    Agar obuna bo'lmagan Telegram kanali bo'lsa — callback orqali ogohlantiradi.
    Aks holda — leveliga qarab kurs yoki menyuga yo'naltiradi.
    """
    user_id = callback.from_user.id

    try:
        channels = await get_all_channels()
        not_subscribed = await check_user_subscriptions(bot, user_id, channels)

        if not_subscribed:
            # Callback orqali ogohlantirish
            await callback.answer("❌ Siz barcha kanallarimizga a'zo bo'lmagansiz!", show_alert=True)
            return
        else:
            # Hamma majburiy kanallarga a'zo bo'lsa → yangi oqim
            await callback.answer("✅ A'zolik tasdiqlandi!", show_alert=False)
            await handle_new_user_flow(callback, user_id)

    except Exception as e:
        logging.error(f"A'zolikni tekshirishda umumiy xatolik: {e}")
        await callback.answer("⚠️ A'zolikni tekshirishda xatolik yuz berdi!", show_alert=True)