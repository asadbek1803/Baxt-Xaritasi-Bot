from aiogram import Router, F, types
from bot.buttons.default.back import get_back_keyboard

router = Router()

@router.message(F.text == "❓ Yordam")
async def help_handler(message: types.Message):
    help_text = """
🔰 Bot bo'yicha yordam:

💳 To'lov tizimi:
 ├ /card - Karta qo'shish
 ├ /buy_course - Kurs sotib olish

👥 Referal tizimi:
 ├ /invite - Referal link olish
 └ /my_group - Mening jamoam

📚 O'quv tizimi:
 ├ /courses - Mavjud kurslar
 ├ /progress - O'quv Progressi
 └ /level - Joriy bosqich

⚙️ Sozlamalar:
 └ /my_profile -Mening profilim

❓ Qo'shimcha yordam uchun adminga murojaat qiling: @admin
"""
    await message.answer(help_text, 
                         reply_markup=get_back_keyboard(), parse_mode="HTML")