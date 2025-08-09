from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.selectors import get_all_active_courses, get_level_kurs, get_user, get_user_level

async def send_course_offer(message: types.Message):
    """Foydalanuvchiga eng so'nggi faol kursni taklif qilish."""
    user_id = str(message.from_user.id)
    
    # Await kalit so'zlarini qo'shamiz
    user = await get_user(chat_id=user_id)
    
    if user:
        user_level = await get_user_level(telegram_id=user_id)
        
        if not user_level:
            await message.reply(
                text="⚠️ Sizning levelingiz aniqlanmagan! Iltimos, qayta ro'yxatdan o'ting."
            )
            return
            
        course = await get_level_kurs(level=user_level)
        print("Kurs: ", course)
        print("User Level: ", user_level)

        if not course:
            await message.reply(
                text="⚠️ Sizning levelingiz uchun hozircha kurs mavjud emas."
            )
            return
               
        text = (
            f"🎓 <b>{course.name}</b>\n\n"
            f"{course.description}\n\n"
            f"💵 Narxi: <b>{course.price} so'm</b>"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buy_course_{course.id}")]
            ]
        )
        
        await message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.reply(
            text="⚠️ Bunday foydalanuvchi mavjud emas! /start buyrug'ini bering."
        )
