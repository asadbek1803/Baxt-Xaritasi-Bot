from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from asgiref.sync import sync_to_async
from aiogram import Router, Bot, F
from bot.selectors import (
    fetch_user, 
    get_all_active_courses_list, 
    get_course_by_user_level,
    get_user_referral_link_async  # Import the new async function
)

from bot.models import TelegramUser

router = Router()

@sync_to_async
def get_user_referrer_info(invited_by):
    if not invited_by:
        return "Yo'q"
    referrer = TelegramUser.objects.filter(telegram_id=invited_by.telegram_id).first()
    if referrer:
        if referrer.telegram_username:
            return f"{referrer.full_name} (@{referrer.telegram_username})"
        return referrer.full_name
    return "Yo'q"

# Remove the old sync function since we now import from selectors
# def get_user_referral_link(user_info): <-- DELETE THIS

# Level mapping dictionary
LEVEL_MAPPING = {
    "0-bosqich": "level_0",
    "1-bosqich": "level_1",
    "2-bosqich": "level_2", 
    "3-bosqich": "level_3",
    "4-bosqich": "level_4",
    "5-bosqich": "level_5",
    "6-bosqich": "level_6",
    "7-bosqich": "level_7",
}

@router.message(F.text == "👤 Mening hisobim")
async def my_profile_handler(message: types.Message, bot: Bot):
    """Foydalanuvchi profilini ko'rsatish"""
    user_id = str(message.from_user.id)
    user_info = await fetch_user(user_id)

    if not user_info:
        await message.answer("❌ Sizning profilingiz topilmadi. Iltimos, avval ro'yxatdan o'ting.")
        return

    print(f"User: {user_info.full_name}, Level: {user_info.level}, is_confirmed: {user_info.is_confirmed}")
    
    # Foydalanuvchi levelini tekshirish
    is_low_level = user_info.level in ["0-bosqich","level_0","1-bosqich", "level_1"]
    
    try:
        # Asosiy profil ma'lumotlari (barcha levellar uchun)
        referrer_info = await get_user_referrer_info(user_info.invited_by) if not is_low_level else "Mavjud emas"
        
        # Telefon raqamni formatlash
        phone_display = user_info.phone_number if user_info.phone_number else "Mavjud emas"
        
        # Username-ni formatlash
        username_display = f"@{user_info.telegram_username}" if user_info.telegram_username else "mavjud emas"
        
        # Jinsni formatlash
        gender_display = "Erkak" if user_info.gender == "M" else "Ayol" if user_info.gender == "F" else "Belgilanmagan"
        
        # Registration date-ni formatlash
        reg_date = user_info.registration_date.strftime('%d.%m.%Y %H:%M') if user_info.registration_date else "Noma'lum"
        
        # Referral count-ni olish (faqat yuqori levellar uchun)
        referral_count = getattr(user_info, 'referral_count', 0) if not is_low_level else 0
        
        profile_info = (
            f"👤 <b>Shaxsiy ma'lumotlar</b>\n"
            f"├ Ism: <b>{user_info.full_name}</b>\n"
            f"├ Yoshi: <b>{user_info.age}</b>\n"
            f"├ Jinsi: <b>{gender_display}</b>\n"
            f"├ Telefon: <code>{phone_display}</code>\n"
            f"├ Username: {username_display}\n"
            f"├ ID: <code>{user_info.telegram_id}</code>\n\n"

            f"📍 <b>Joylashuv</b>\n"
            f"├ Hudud: <b>{user_info.region}</b>\n"
            f"├ Kasbi: <b>{user_info.profession}</b>\n\n"

            f"📅 <b>Faollik</b>\n"
            f"├ Ro'yxatdan o'tgan: <b>{reg_date}</b>\n"
            f"├ Level: <b>{user_info.level}</b>\n\n"
        )
        
        # Referal tizimi (barcha levellar uchun ko'rsatamiz)
        profile_info += (
            f"👥 <b>Referal tizimi</b>\n"
            f"├ Taklif qilgan: <b>{referrer_info}</b>\n"
            f"├ Taklif qilganlar soni: <b>{referral_count} ta</b>\n"
        )
        
        # Referal link olish (faqat tasdiqlangan userlar uchun)
        if user_info.is_confirmed:
            try:
                referral_link = await get_user_referral_link_async(user_info)  # Use async function
                profile_info += f"└ Referal link: <code>{referral_link}</code>\n\n"
            except Exception as e:
                print(f"Error getting referral link: {e}")
                profile_info += "└ Referal link: Xatolik\n\n"
        else:
            profile_info += "└ Referal link: 🔒 Tasdiqlanganidan keyin mavjud bo'ladi\n\n"
        
        # Tasdiqlash holati
        status_text = "✅ Tasdiqlangan admin tomonidan" if user_info.is_confirmed else "⏳ Tasdiqlanmagan"
        profile_info += f"🛡 <b>Status</b>\n└ {status_text}"

        # Keyboard yaratish (levelga va tasdiqlash holatiga qarab)
        builder = InlineKeyboardBuilder()
        
        # is_confirmed ga qarab tugmalarni ko'rsatish
        if user_info.is_confirmed:
            # Tasdiqlangan userlar uchun statistika va referal link tugmalari
            builder.row(
                types.InlineKeyboardButton(
                    text="📊 Statistikani ko'rish",
                    callback_data=f"stats_{user_info.telegram_id}"
                )
            )
            builder.row(
                types.InlineKeyboardButton(
                    text="📋 Referal linkni nusxalash",
                    callback_data=f"copy_ref_{user_info.telegram_id}"
                )
            )
            builder.row(
            types.InlineKeyboardButton(
                text="💳 Plastik karta ma'lumotlari",
                callback_data=f"card_info_{user_info.telegram_id}"
            )
        )
        else:
            # Tasdiqlanmagan userlar uchun kurs sotib olish va referal yaratish tugmalari
            try:
                course = await get_course_by_user_level(user_info.level)
                if course:
                    builder.row(
                        types.InlineKeyboardButton(
                            text="🛒 Kurs sotib olish",
                            callback_data=f"buy_course_{course.id}"
                        )
                    )
                    builder.row(
                        types.InlineKeyboardButton(
                            text="📢 Referral yaratish",
                            callback_data=f"create_referral_{course.id}"
                        )
                    )
        
            except Exception as e:
                print(f"Error getting course for buttons: {e}")

        # Profil ma'lumotlarini yuborish
        if builder.export():
            await message.answer(
                text=profile_info,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=profile_info,
                parse_mode="HTML"
            )
        
    except Exception as e:
        print(f"Error showing profile: {e}")
        await message.answer("❌ Profil ma'lumotlarini olishda xatolik yuz berdi.")


@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_referral_link(callback: types.CallbackQuery):
    """Referal linkni nusxalash - faqat tasdiqlangan userlar uchun"""
    try:
        user_id = callback.data.split("_")[2]
        user_info = await fetch_user(user_id)
        
        if not user_info:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
        
        # Tasdiqlash tekshirish
        if not user_info.is_confirmed:
            await callback.answer("🔒 Bu funksiya faqat tasdiqlangan foydalanuvchilar uchun!", show_alert=True)
            return
        
        referral_link = await get_user_referral_link_async(user_info)  # Use async function
        await callback.message.answer(
            f"📋 <b>Referal link</b>\n\n"
            f"Quyidagi linkni nusxalash uchun bosing:\n\n"
            f"<code>{referral_link}</code>\n\n"
            f"Bu link orqali sizga taklif qilingan har bir yangi foydalanuvchi uchun bonus olasiz!",
            parse_mode="HTML"
        )
        await callback.answer("✅ Referal link yuborildi!", show_alert=False)
        
    except Exception as e:
        print(f"Error copying referral link: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("stats_"))
async def show_user_stats(callback: types.CallbackQuery):
    """Foydalanuvchi statistikasini ko'rsatish - faqat tasdiqlangan userlar uchun"""
    try:
        user_id = callback.data.split("_")[1]
        user_info = await fetch_user(user_id)
        
        if not user_info:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
        
        # Tasdiqlash tekshirish
        if not user_info.is_confirmed:
            await callback.answer("🔒 Bu funksiya faqat tasdiqlangan foydalanuvchilar uchun!", show_alert=True)
            return
        
        # Referral count-ni olish
        referral_count = getattr(user_info, 'referral_count', 0)
        
        # Registration date-ni formatlash
        reg_date = user_info.registration_date.strftime('%d.%m.%Y') if user_info.registration_date else "Noma'lum"
        
        stats_info = (
            f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
            f"👤 <b>{user_info.full_name}</b>\n"
            f"🆔 ID: <code>{user_info.telegram_id}</code>\n\n"
            f"👥 Taklif qilganlar soni: <b>{referral_count} ta</b>\n"
            f"📅 Ro'yxatdan o'tgan: <b>{reg_date}</b>\n"
            f"🎯 Level: <b>{user_info.level}</b>\n"
            f"✅ Status: <b>{'Tasdiqlangan' if user_info.is_confirmed else 'Tasdiqlanmagan'}</b>\n\n"
        )
        
        # Referal link qo'shish
        try:
            referral_link = await get_user_referral_link_async(user_info)  # Use async function
            stats_info += f"🔗 Referal link: <code>{referral_link}</code>"
        except Exception as e:
            print(f"Error getting referral link in stats: {e}")
            stats_info += "🔗 Referal link: Xatolik"
        
        await callback.message.answer(
            text=stats_info,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing stats: {e}")
        await callback.answer("❌ Statistikani olishda xatolik!", show_alert=True)