from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types
from asgiref.sync import sync_to_async
from aiogram import Router, Bot, F
from bot.selectors import fetch_user, get_all_active_courses,get_user_active_payments
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

@router.message(F.text == "👤 Mening hisobim")
async def my_profile_handler(message: types.Message, bot: Bot):
    user_id = str(message.from_user.id)
    if get_user_active_payments(user_id) == True:

        user_info = await fetch_user(user_id)
        
        if not user_info:
            await message.answer("❌ Sizning profilingiz topilmadi. Iltimos, avval ro'yxatdan o'ting.")
            return
        
        # Async kontekstda sync funksiyalarni chaqirish
        referrer_info = await get_user_referrer_info(user_info.invited_by)
        
        # Profil ma'lumotlari
        profile_info = (
            f"👤 <b>Shaxsiy ma'lumotlar</b>\n"
            f"├ Ism: <b>{user_info.full_name}</b>\n"
            f"├ Yoshi: <b>{user_info.age}</b>\n"
            f"├ Jinsi: <b>{'Erkak' if user_info.gender == 'M' else 'Ayol'}</b>\n"
            f"├ Telefon: <code>{user_info.phone_number}</code>\n"
            f"├ Username: @{user_info.telegram_username if user_info.telegram_username else 'mavjud emas'}\n"
            f"├ ID: <code>{user_info.telegram_id}</code>\n\n"
            
            f"📍 <b>Joylashuv</b>\n"
            f"├ Hudud: <b>{user_info.region}</b>\n"
            f"├ Kasbi: <b>{user_info.profession}</b>\n\n"
            
            f"📅 <b>Faollik</b>\n"
            f"├ Ro'yxatdan o'tgan: <b>{user_info.registration_date.strftime('%d.%m.%Y %H:%M')}</b>\n"
            
            f"👥 <b>Referal tizimi</b>\n"
            f"├ Taklif qilgan: <b>{referrer_info}</b>\n"
            f"├ Taklif qilganlar soni: <b>{user_info.referral_count} ta</b>\n"
            f"└ Referal link: <code>{await sync_to_async(user_info.get_referral_link)()}</code>\n\n"
            
            f"🛡 <b>Status</b>\n"
            f"{'└ ✅ Tasdiqlangan admin tomonidan' if user_info.is_confirmed else '└ ⏳ Tasdiqlanmagan'}"
        )

        # Tugmalar yaratish
        builder = InlineKeyboardBuilder()
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

        await message.answer(
            text=profile_info,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Iltimos botdan to'liq foydalanish uchun avval kurs sotib oling.",
        )
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
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_referral_link(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[2]
    user_info = await fetch_user(user_id)
    
    if not user_info:
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
        return
    
    referral_link = await sync_to_async(user_info.get_referral_link)()
    await callback.message.answer(
        f"📋 Quyidagi referal linkni nusxalash uchun bosing:\n\n"
        f"<code>{referral_link}</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Referal link nusxalandi!", show_alert=True)


@router.callback_query(F.data.startswith("stats_"))
async def show_user_stats(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[1]
    user_info = await fetch_user(user_id)
    
    if not user_info:
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
        return
    
    stats_info = (
        f"📊 <b>Foydalanuvchi statistikasi</b>\n\n"
        f"👥 Taklif qilganlar soni: <b>{user_info.referral_count} ta</b>\n"
        f"📅 Ro'yxatdan o'tgan sana: <b>{user_info.registration_date.strftime('%d.%m.%Y')}</b>\n"
        f"🔗 Referal link: <code>{await sync_to_async(user_info.get_referral_link)()}</code>"
    )
    
    await callback.message.answer(
        text=stats_info,
        parse_mode="HTML"
    )
    await callback.answer()