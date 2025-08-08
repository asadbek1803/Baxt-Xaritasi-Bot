from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.selectors import get_all_channels, get_user, get_all_active_courses, get_user_buy_course
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard as get_menu_buttons
import logging
import html

router = Router()

@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    message = callback.message
    
    await callback.answer("⏳ A'zolik tekshirilmoqda...", show_alert=False)

    try:
        channels = await get_all_channels()
    except Exception as e:
        logging.error(f"Kanallarni olishda xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring!", show_alert=True)
        return

    not_subscribed_channels = []

    for channel in channels:
        is_telegram = getattr(channel, "is_telegram", True)
        is_private = getattr(channel, "is_private", False)
        
        if is_telegram and getattr(channel, "telegram_id", None):
            try:
                member = await bot.get_chat_member(
                    chat_id=channel.telegram_id,
                    user_id=user_id
                )
                
                # ⭐ Asosiy o'zgarish: restricted statusini ham a'zo deb hisoblaymiz
                if member.status in ['left', 'kicked']:
                    not_subscribed_channels.append(channel)

            except TelegramBadRequest as e:
                logging.error(f"A'zolik tekshirishda xatolik: {e}")
                not_subscribed_channels.append(channel)
            except TelegramForbiddenError:
                logging.error(f"Bot kanaldan chiqarib yuborilgan yoki unga kira olmaydi: {channel.name}")
                not_subscribed_channels.append(channel)
            except Exception as e:
                logging.error(f"A'zolik tekshirishda kutilmagan xatolik: {e}")
                not_subscribed_channels.append(channel)
        else:
            not_subscribed_channels.append(channel)

    try:
        if not not_subscribed_channels:
            await callback.answer("✅ Tabriklaymiz! Siz barcha kanallarga a'zo bo'lgansiz!", show_alert=True)
            user = await get_user(callback.message.from_user.id)
            if await get_user_buy_course(telegram_id = user_id) == True:
                
                await callback.message.answer(
                    text = Messages.welcome_message.value.format(
                        full_name = user.full_name
                    ),
                    reply_markup = get_menu_buttons()
                )
                return
            # Foydalanuvchi kurs sotib olmagan bo‘lsa
            courses = await get_all_active_courses()
            if courses:
                course = courses[0]  # Eng oxirgi faol kurs
                text = (
                    f"🎓 <b>{course.name}</b>\n\n"
                    f"{course.description}\n\n"
                    f"💵 Narxi: <b>{course.price} so'm</b>"
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🛒 Sotib olish",
                                callback_data=f"buy_course_{course.id}"
                            )
                        ]
                    ]
                )
                await callback.message.answer(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return
        else:
            channel_names = [html.escape(ch.name or "Kanal") for ch in not_subscribed_channels]
            await callback.answer(
                f"❌ Quyidagi kanallarga hali a'zo bo'lmagansiz: {', '.join(channel_names)}",
                show_alert=True
            )
            # Faqat a'zo bo'lmagan kanallar bo'lsa, xabar o'chirilmaydi
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)