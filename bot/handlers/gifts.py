from aiogram import Router, F, types
from bot.selectors import get_gifts_is_active
from bot.buttons.default.back import get_back_keyboard

router = Router()

@router.message(F.text == "🏆 Sovg'alar")
async def gifts_handler(message: types.Message):
    gifts = await get_gifts_is_active()
    if not gifts:
        await message.answer("🏆 <b>Sovg'alar mavjud emas</b>", parse_mode="HTML")
        return

    # Eng birinchi (yangi) gift
    gift = gifts[0]

    gifts_text = "🏆 <b>Sovg'alar:</b>\n\n"
    gifts_text += f"\n\n"
    gifts_text += f"<i>{gift.description}</i>\n"

    # Rasm bor bo'lsa rasm + caption jo'natamiz
    if gift.image:
        file_path = gift.image.path  # to‘liq fayl yo‘li
        await message.answer_photo(
            photo=types.FSInputFile(file_path),
            caption=gifts_text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(gifts_text, parse_mode="HTML",
                             reply_markup=get_back_keyboard())
