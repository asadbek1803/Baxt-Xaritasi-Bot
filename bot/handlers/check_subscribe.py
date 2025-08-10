from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

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
import html

router = Router()

@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    await callback.answer("⏳ A'zolik tekshirilmoqda...")

    try:
        channels = await get_all_channels()
    except Exception as e:
        logging.error(f"Kanallarni olishda xatolik: {e}")
        return await callback.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring!", show_alert=True)

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
            logging.error(f"Bot {channel.name} kanalida ishlay olmaydi: {e}")
            not_subscribed.append(channel)
        except Exception as e:
            logging.error(f"A'zolik tekshiruv xatosi: {e}")
            not_subscribed.append(channel)

    if not not_subscribed:
        user = await get_user(user_id)
        user_level = await get_user_level(telegram_id=user_id)

        # Agar foydalanuvchi 1-bosqich bo'lsa
        if user_level == "0-bosqich":
            if await get_user_buy_course(telegram_id=user_id):
                return await callback.message.answer(
                    text=Messages.welcome_message.value.format(full_name=user.full_name),
                    reply_markup=get_menu_keyboard()
                )
            
            # Levelga mos kursni olish
            course = await get_level_kurs(level=user_level)
            if course:
                text = (
                    f"🎓 <b>{course.name}</b>\n\n"
                    f"{course.description}\n\n"
                    f"💵 Narxi: <b>{course.price} so'm</b>"
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="🛒 Sotib olish",
                            callback_data=f"buy_course_{course.id}"
                        ),
                        InlineKeyboardButton(
                            text = "📢 Referralimni yaratish",
                            callback_data=f"create_referral_{course.id}"
                        )
                    ]]
                )
                return await callback.message.answer(
                    text=text, parse_mode="HTML", reply_markup=keyboard
                )
        else:
            # 1-bosqich bo'lmagan foydalanuvchi uchun menyu
            return await callback.message.answer(
                text=Messages.welcome_message.value.format(full_name=user.full_name),
                reply_markup=get_menu_keyboard()
            )
    else:
        channels_str = ", ".join(html.escape(ch.name or "Kanal") for ch in not_subscribed)
        await callback.answer(
            f"❌ Quyidagi kanallarga hali a'zo bo'lmadingiz: {channels_str}",
            show_alert=True
        )
