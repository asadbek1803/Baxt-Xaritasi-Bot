from aiogram import types, F, Router
from bot.buttons.default.back import get_back_keyboard

router = Router()

@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: types.Message):
    await message.answer(
        "📞 <b>Aloqa uchun ma'lumotlar</b>\n\n"
        "📧 <b>Email:</b> example@gmail.com\n"
        "📱 <b>Telefon:</b> +998 90 123-45-67\n"
        "📍 <b>Manzil:</b> Toshkent sh., Example ko'chasi, 123-uy\n"
        "🌐 <b>Telegram:</b> @example_support\n"
        "⏰ <b>Ish vaqti:</b> 09:00 - 18:00",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )