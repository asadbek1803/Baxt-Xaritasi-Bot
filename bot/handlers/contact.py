from aiogram import types, F, Router
from bot.buttons.default.back import get_back_keyboard

router = Router()


@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: types.Message):
    await message.answer(
        "📞 <b>Aloqa uchun ma'lumotlar</b>\n\n"
        "📱 <b>Telefon:</b> +998915971000\n"
        "🌐 <b>Telegram:</b> @PsixologGulhayoMuminova\n",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )
