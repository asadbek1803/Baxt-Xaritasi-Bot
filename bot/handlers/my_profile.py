# my_profile.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from aiogram import Router, Bot, F
from bot.selectors import (
    get_user_profile_by_telegram_id,
    get_referrer_display_by_telegram_id,
    get_course_for_next_level_by_user_level,
    get_referral_link_for_user,
)
from bot.buttons.default.back import get_back_keyboard

router = Router()


def format_user_level(level: str) -> str:
    """
    level may be 'level_1' or '1-bosqich' or None -> return 'N-bosqich' style
    """
    if not level:
        return "0-bosqich"
    if isinstance(level, str) and level.startswith("level_"):
        try:
            num = level.split("_")[1]
            return f"{num}-bosqich"
        except Exception:
            return level
    return level


@router.message(F.text == "👤 Mening hisobim")
async def my_profile_handler(message: types.Message, bot: Bot):
    try:
        user_id = str(message.from_user.id)

        # Get user profile data (all DB work inside sync_to_async)
        user_data = await get_user_profile_by_telegram_id(user_id)

        if not user_data:
            await message.answer(
                "❌ Sizning profilingiz topilmadi. Iltimos, avval ro'yxatdan o'ting."
            )
            return
        # Foydalanuvchi darajasini formatlash
        if user_data.get("level") == "level_0" or user_data.get("level") == "0-bosqich":

            await bot.send_message(
                chat_id=user_id,
                text="🔒 Sizning darajangiz 0-daraja (1-darjaga) o'tish uchun '⚡️ Bosqichlar' bo'limidan 1-kursni sotib oling!",
            )
            return

        user_level_formatted = format_user_level(user_data.get("level"))

        # Referrer display (we already have invited_by in user_data, but use helper to be safe)
        invited = user_data.get("invited_by")
        if invited:
            if invited.get("telegram_username"):
                referrer_display = (
                    f"{invited.get('full_name')} (@{invited.get('telegram_username')})"
                )
            else:
                referrer_display = invited.get("full_name") or "Yo'q"
        else:
            # fallback: try selector that formats inviter display
            referrer_display = (
                await get_referrer_display_by_telegram_id(invited.get("telegram_id"))
                if invited
                else "Yo'q"
            )

        profile_info = (
            f"👤 <b>Shaxsiy ma'lumotlar</b>\n"
            f"├ Ism: <b>{user_data['full_name']}</b>\n"
            f"├ Yoshi: <b>{user_data['age']}</b>\n"
            f"├ Jinsi: <b>{user_data['gender']}</b>\n"
            f"├ Telefon: <code>{user_data['phone']}</code>\n"
            f"├ Username: {user_data['username']}\n"
            f"├ ID: <code>{user_data['telegram_id']}</code>\n\n"
            f"📍 <b>Joylashuv</b>\n"
            f"├ Hudud: <b>{user_data['region']}</b>\n"
            f"├ Kasbi: <b>{user_data['profession']}</b>\n\n"
            f"📅 <b>Faollik</b>\n"
            f"├ Ro'yxatdan o'tgan: <b>{user_data['registration_date']}</b>\n\n"
            f"👥 <b>Referal tizimi</b>\n"
            f"├ Taklif qilgan: <b>{referrer_display}</b>\n"
            f"├ Taklif qilganlar soni: <b>{user_data['referral_count']} ta</b>\n"
        )

        # Referal link (faqat tasdiqlangan userlar uchun)
        if user_data.get("is_confirmed"):
            try:
                referral_link = await get_referral_link_for_user(
                    user_data["telegram_id"]
                )
                profile_info += f"└ Referal link: <code>{referral_link}</code>\n\n"
            except Exception as e:
                print(f"[my_profile_handler] Error getting referral link: {e}")
                profile_info += "└ Referal link: Xatolik\n\n"
        else:
            profile_info += (
                "└ Referal link: 🔒 Tasdiqlanganidan keyin mavjud bo'ladi\n\n"
            )

        # Status
        status_text = (
            "✅ Tasdiqlangan admin tomonidan"
            if user_data.get("is_confirmed")
            else "⏳ Tasdiqlanmagan"
        )
        profile_info += f"🛡 <b>Status</b>\n└ {status_text}"

        # Create keyboard
        builder = InlineKeyboardBuilder()

        if user_data.get("is_confirmed"):
            builder.row(
                types.InlineKeyboardButton(
                    text="📊 Statistikani ko'rish",
                    callback_data=f"stats_{user_data['telegram_id']}",
                )
            )
            builder.row(
                types.InlineKeyboardButton(
                    text="📋 Referal linkni nusxalash",
                    callback_data=f"copy_ref_{user_data['telegram_id']}",
                )
            )
        else:
            # show course-related buttons
            try:
                course = await get_course_for_next_level_by_user_level(
                    user_data.get("level")
                )
                if course:
                    if not user_data.get("is_confirmed"):
                        builder.row(
                            types.InlineKeyboardButton(
                                text="📢 Referral yaratish",
                                callback_data=f"create_referral_{course['id']}",
                            )
                        )
                        profile_info += (
                            f"\n\n<b>⚠️ Darajani oshirish uchun ⚠️ </b>\n"
                            f"1. Referral yaratish: <b>{course['referral_name']}</b>"
                        )

                    builder.row(
                        types.InlineKeyboardButton(
                            text="🛒 Kurs sotib olish",
                            callback_data=f"buy_course_{course['id']}",
                        )
                    )

            except Exception as e:
                print(f"[my_profile_handler] Error getting course for buttons: {e}")
        builder.row(
            types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_to_home")
        )
        # Send message with or without keyboard
        try:
            if builder.export():
                await message.answer(
                    text=profile_info,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    text=profile_info,
                    parse_mode="HTML",
                    reply_markup=get_back_keyboard(),
                )
        except Exception as e:
            print(f"[my_profile_handler] Send message error: {e}")
            await message.answer(
                "❌ Profil ma'lumotlarini yuborishda xatolik yuz berdi."
            )

    except Exception as e:
        print(f"[my_profile_handler] Unexpected error: {e}")
        await message.answer("❌ Profil ma'lumotlarini olishda xatolik yuz berdi.")


@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_referral_link(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Xato callback data!", show_alert=True)
            return
        user_id = parts[2]

        user_data = await get_user_profile_by_telegram_id(user_id)
        if not user_data:
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        if not user_data.get("is_confirmed"):
            await callback.answer(
                "🔒 Bu funksiya faqat tasdiqlangan foydalanuvchilar uchun!",
                show_alert=True,
            )
            return

        referral_link = await get_referral_link_for_user(user_id)
        await callback.message.answer(
            f"📋 <b>Referal link</b>\n\n"
            f"Quyidagi linkni nusxalash uchun bosing:\n\n"
            f"<code>{referral_link}</code>\n\n"
            f"Bu link orqali sizga taklif qilingan har bir yangi foydalanuvchi uchun bonus olasiz!",
            parse_mode="HTML",
        )
        await callback.answer("✅ Referal link yuborildi!", show_alert=False)

    except Exception as e:
        print(f"[copy_referral_link] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("stats_"))
async def show_user_stats(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        if len(parts) < 2:
            await callback.answer("❌ Xato callback data!", show_alert=True)
            return
        user_id = parts[1]

        user_data = await get_user_profile_by_telegram_id(user_id)
        if not user_data:
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        if not user_data.get("is_confirmed"):
            await callback.answer(
                "🔒 Bu funksiya faqat tasdiqlangan foydalanuvchilar uchun!",
                show_alert=True,
            )
            return

        stats_info = (
            f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
            f"👤 <b>{user_data['full_name']}</b>\n"
            f"🆔 ID: <code>{user_data['telegram_id']}</code>\n\n"
            f"👥 Taklif qilganlar soni: <b>{user_data['referral_count']} ta</b>\n"
            f"📅 Ro'yxatdan o'tgan: <b>{user_data['registration_date']}</b>\n"
            f"🎯 Level: <b>{user_data['level']}</b>\n"
            f"✅ Status: <b>{'Tasdiqlangan' if user_data['is_confirmed'] else 'Tasdiqlanmagan'}</b>\n\n"
        )

        try:
            referral_link = await get_referral_link_for_user(user_data["telegram_id"])
            stats_info += f"🔗 Referal link: <code>{referral_link}</code>"
        except Exception as e:
            print(f"[show_user_stats] Error getting referral link: {e}")
            stats_info += "🔗 Referal link: Xatolik"

        await callback.message.answer(text=stats_info, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        print(f"[show_user_stats] Error: {e}")
        await callback.answer("❌ Statistikani olishda xatolik!", show_alert=True)
