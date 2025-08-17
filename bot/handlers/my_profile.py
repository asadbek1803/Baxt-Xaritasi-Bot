from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from aiogram import Router, Bot, F
from django.utils import timezone

from bot.selectors import (
    get_user_profile_by_telegram_id,
    get_referrer_display_by_telegram_id,
    get_referral_link_for_user,
)
from bot.buttons.default.back import get_back_keyboard
from bot.models import TelegramUser

router = Router()


# Test handler to verify callback queries are working
@router.callback_query(F.data == "test_callback")
async def test_callback(callback: types.CallbackQuery):
    """Test callback handler"""
    print(f"[DEBUG] Test callback received from user {callback.from_user.id}")
    await callback.answer("Test callback working!", show_alert=True)


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

        # Referal link (referral_code mavjud bo'lsa)
        if user_data.get("referral_code"):
            try:
                referral_link = await get_referral_link_for_user(
                    user_data["telegram_id"]
                )
                profile_info += f"└ Referal link: <code>{referral_link}</code>\n\n"
            except Exception as e:
                print(f"[my_profile_handler] Error getting referral link: {e}")
                profile_info += "└ Referal link: Xatolik\n\n"
        else:
            profile_info += "└ Referal link: Mavjud emas\n\n"

        # Status
        status_text = (
            "✅ Tasdiqlangan admin tomonidan"
            if user_data.get("is_confirmed")
            else "⏳ Tasdiqlanmagan"
        )
        profile_info += f"🛡 <b>Status</b>\n└ {status_text}"

        # Create keyboard
        builder = InlineKeyboardBuilder()

        # Tugmalar faqat referral_code mavjud bo'lsa ko'rsatiladi
        if user_data.get("referral_code"):
            print(f"[DEBUG] Creating statistics button for user {user_id}")
            builder.row(
                types.InlineKeyboardButton(
                    text="📊 Statistikani ko'rish",
                    callback_data="stats",
                )
            )

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


@router.message(F.text == "🔗 Mening havolam")
async def my_referral_link_handler(message: types.Message):
    """Foydalanuvchining referral linkini ko'rsatish"""
    try:
        user_id = str(message.from_user.id)
        print(f"[DEBUG] Referral link requested by user {user_id}")

        # Get user profile data
        user_data = await get_user_profile_by_telegram_id(user_id)

        if not user_data:
            await message.answer(
                "❌ Sizning profilingiz topilmadi. Iltimos, avval ro'yxatdan o'ting."
            )
            return

        if not user_data.get("referral_code"):
            await message.answer(
                "❌ Sizda referal kodi mavjud emas! Iltimos, admin bilan bog'laning."
            )
            return

        # Get referral link
        try:
            referral_link = await get_referral_link_for_user(user_id)
            print(
                f"[DEBUG] Referral link generated for user {user_id}: {referral_link}"
            )
        except Exception as e:
            print(f"[DEBUG] Error getting referral link for user {user_id}: {e}")
            await message.answer("❌ Referral link olishda xatolik yuz berdi.")
            return

        # Create keyboard with share and copy options
        builder = InlineKeyboardBuilder()

        # Share button
        share_text = (
            f"🎯 Pul ishlash imkoniyati!\n\n"
            f"💰 Referral dasturi orqali daromad oling!\n"
            f"📈 Har bir yangi a'zo uchun bonus!\n\n"
            f"🔗 Qo'shilish uchun: {referral_link}\n\n"
            f"⚡️ Imkoniyatni qo'ldan boy bermang!"
        )
        builder.row(
            types.InlineKeyboardButton(
                text="📤 Ulashish", switch_inline_query=share_text
            )
        )

        # Back to menu button
        builder.row(
            types.InlineKeyboardButton(
                text="🔙 Menyuga qaytish", callback_data="back_to_home"
            )
        )

        # Send referral link message
        await message.answer(
            f"🔗 <b>Sizning referral linkingiz</b>\n\n"
            f"<code>{referral_link}</code>\n\n"
            f"📤 <b>Ulashish:</b> Pastdagi tugma orqali do'stlaringiz, guruhlar yoki kanallarga ulashing\n\n",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )

        print(f"[DEBUG] Referral link sent successfully to user {user_id}")

    except Exception as e:
        print(f"[my_referral_link_handler] Error: {e}")
        await message.answer("❌ Referral link olishda xatolik yuz berdi.")


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

        if not user_data.get("referral_code"):
            await callback.answer(
                "❌ Sizda referal kodi mavjud emas!",
                show_alert=True,
            )
            return

        referral_link = await get_referral_link_for_user(user_id)

        # Share button tugmasi yaratish
        builder = InlineKeyboardBuilder()

        # Referral link va reklama matni
        share_text = (
            f"🎯 Pul ishlash imkoniyati!\n\n"
            f"💰 Referral dasturi orqali daromad oling!\n"
            f"📈 Har bir yangi a'zo uchun bonus!\n\n"
            f"🔗 Qo'shilish uchun: {referral_link}\n\n"
            f"⚡️ Imkoniyatni qo'ldan boy bermang!"
        )
        builder.row(
            types.InlineKeyboardButton(
                text="📤 Ulashish", switch_inline_query=share_text
            )
        )
        # Linkni nusxalash tugmasi
        builder.row(
            types.InlineKeyboardButton(
                text="📋 Linkni nusxalash", callback_data=f"copy_link_{user_id}"
            )
        )
        # Ortga qaytish tugmasi
        builder.row(
            types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_to_profile")
        )

        await callback.message.edit_text(
            f"📋 <b>Referal linkni ulashish</b>\n\n"
            f"🔗 Sizning referal linkingiz:\n"
            f"<code>{referral_link}</code>\n\n"
            f"📤 <b>Ulashish:</b> Pastdagi tugma orqali do'stlaringiz, guruhlar yoki kanallarga ulashing\n\n"
            f"📋 <b>Nusxalash:</b> Linkni nusxalab olish uchun tegishli tugmani bosing\n\n"
            f"💡 <b>Maslahat:</b> Link orqali ro'yxatdan o'tgan har bir yangi foydalanuvchi uchun bonus olasiz!",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()

    except Exception as e:
        print(f"[copy_referral_link] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


# Qo'shimcha callback handlerlar


@router.callback_query(F.data.startswith("copy_link_"))
async def copy_link_only(callback: types.CallbackQuery):
    """Faqat linkni nusxalash uchun"""
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Xato callback data!", show_alert=True)
            return
        user_id = parts[2]

        referral_link = await get_referral_link_for_user(user_id)

        await callback.answer(f"📋 Link nusxalandi:\n{referral_link}", show_alert=True)

    except Exception as e:
        print(f"[copy_link_only] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data == "stats")
async def show_user_stats(callback: types.CallbackQuery):
    try:
        user_id = str(callback.from_user.id)
        print(f"[DEBUG] Getting profile data for user {user_id}")
        user_data = await get_user_profile_by_telegram_id(user_id)

        if not user_data:
            print(f"[DEBUG] No user data found for user {user_id}")
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        print(f"[DEBUG] User data retrieved successfully for user {user_id}")

        if not user_data.get("referral_code"):
            print(f"[DEBUG] User {user_id} has no referral code")
            await callback.answer(
                "❌ Sizda referal kodi mavjud emas!",
                show_alert=True,
            )
            return

        print(
            f"[DEBUG] User {user_id} has referral code: {user_data.get('referral_code')}"
        )

        stats_info = (
            f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
            f"👤 <b>{user_data['full_name']}</b>\n"
            f"🆔 ID: <code>{user_data['telegram_id']}</code>\n\n"
            f"👥 Taklif qilganlar soni: <b>{user_data['referral_count']} ta</b>\n"
            f"📅 Ro'yxatdan o'tgan: <b>{user_data['registration_date']}</b>\n"
            f"🎯 Level: <b>{user_data['level']}</b>\n"
            f"✅ Status: <b>{'Tasdiqlangan' if user_data['is_confirmed'] else 'Tasdiqlanmagan'}</b>\n\n"
        )
        print(f"[DEBUG] Stats info created: {len(stats_info)} characters")

        try:
            print(f"[DEBUG] Getting referral link for user {user_data['telegram_id']}")
            referral_link = await get_referral_link_for_user(user_data["telegram_id"])
            stats_info += f"🔗 Referal link: <code>{referral_link}</code>"
            print(f"[DEBUG] Referral link generated successfully: {referral_link}")
        except Exception as e:
            print(f"[show_user_stats] Error getting referral link: {e}")
            stats_info += "🔗 Referal link: Xatolik"

        # Create keyboard with back button
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_to_profile")
        )
        print(f"[DEBUG] Created back button with callback_data: back_to_profile")

        print(f"[DEBUG] Sending statistics for user {user_id}")
        try:
            await callback.message.edit_text(
                text=stats_info, parse_mode="HTML", reply_markup=builder.as_markup()
            )
            print(f"[DEBUG] Statistics edited successfully for user {user_id}")
        except Exception as edit_error:
            print(
                f"[DEBUG] Edit failed for user {user_id}, sending new message: {edit_error}"
            )
            # Fallback: send new message if editing fails
            await callback.message.answer(
                text=stats_info, parse_mode="HTML", reply_markup=builder.as_markup()
            )
            print(f"[DEBUG] Statistics sent as new message for user {user_id}")

        try:
            await callback.answer()
            print(f"[DEBUG] Callback answered successfully for user {user_id}")
        except Exception as answer_error:
            print(f"[DEBUG] Callback answer failed for user {user_id}: {answer_error}")

        print(f"[DEBUG] Statistics sent successfully for user {user_id}")

    except Exception as e:
        print(f"[show_user_stats] Error: {e}")
        await callback.answer("❌ Statistikani olishda xatolik!", show_alert=True)


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile_handler(callback: types.CallbackQuery):
    """Profilga qaytish"""
    try:
        # Profilni qayta ko'rsatish uchun my_profile_handler logikasini chaqiramiz
        user_id = str(callback.from_user.id)
        user_data = await get_user_profile_by_telegram_id(user_id)

        if not user_data:
            await callback.answer("❌ Profil topilmadi!", show_alert=True)
            return

        # Profilni qayta tiklash
        invited = user_data.get("invited_by")
        if invited:
            if invited.get("telegram_username"):
                referrer_display = (
                    f"{invited.get('full_name')} (@{invited.get('telegram_username')})"
                )
            else:
                referrer_display = invited.get("full_name") or "Yo'q"
        else:
            referrer_display = "Yo'q"

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

        # Referal link
        if user_data.get("referral_code"):
            try:
                referral_link = await get_referral_link_for_user(
                    user_data["telegram_id"]
                )
                profile_info += f"└ Referal link: <code>{referral_link}</code>\n\n"
            except Exception as e:
                print(f"Error getting referral link: {e}")
                profile_info += "└ Referal link: Xatolik\n\n"
        else:
            profile_info += "└ Referal link: Mavjud emas\n\n"

        # Status
        status_text = (
            "✅ Tasdiqlangan admin tomonidan"
            if user_data.get("is_confirmed")
            else "⏳ Tasdiqlanmagan"
        )
        profile_info += f"🛡 <b>Status</b>\n└ {status_text}"

        # Tugmalar
        builder = InlineKeyboardBuilder()

        if user_data.get("referral_code"):
            builder.row(
                types.InlineKeyboardButton(
                    text="📊 Statistikani ko'rish",
                    callback_data="stats",
                )
            )

        builder.row(
            types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_to_home")
        )

        await callback.message.edit_text(
            text=profile_info, parse_mode="HTML", reply_markup=builder.as_markup()
        )
        await callback.answer()

    except Exception as e:
        print(f"[back_to_profile_handler] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("confirm_activity_"))
async def confirm_user_activity(callback: types.CallbackQuery):
    """Foydalanuvchi aktivligini tasdiqlash"""
    try:
        # Extract user ID from callback data
        user_id = callback.data.split("_")[2]

        print(f"[DEBUG] Activity confirmation requested for user {user_id}")

        # Get user data
        user_data = await get_user_profile_by_telegram_id(user_id)

        if not user_data:
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        # Check if the user is confirming their own activity
        if str(callback.from_user.id) != user_id:
            await callback.answer("❌ Bu tugma siz uchun emas!", show_alert=True)
            return

        user = TelegramUser.objects.get(telegram_id=user_id)
        user.is_active = True
        user.deadline_for_activation = None
        user.last_activity_check = timezone.now()
        user.save()

        print(f"[DEBUG] User {user_id} activity confirmed successfully")

        # Delete the message with the button
        try:
            await callback.message.delete()
        except Exception as e:
            print(f"[DEBUG] Could not delete message: {e}")

        # Send confirmation message
        await callback.message.answer(
            "✅ <b>Aktivlik tasdiqlandi!</b>\n\n"
            "Siz muvaffaqiyatli ravishda aktiv foydalanuvchi sifatida tasdiqlandingiz.\n"
            "Endi siz botimizning barcha funksiyalaridan foydalana olasiz.",
            parse_mode="HTML",
        )

        await callback.answer("✅ Aktivlik tasdiqlandi!")

    except Exception as e:
        print(f"[confirm_user_activity] Error: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
