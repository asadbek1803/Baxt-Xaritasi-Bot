from aiogram import Router, Bot, F, types
from bot.constants import Button
from bot.buttons.default.menu import get_menu_keyboard as get_menu_buttons
from aiogram.fsm.context import FSMContext
router = Router()

@router.message(F.text == Button.back.value)
async def handle_back_button(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    try:
        await bot.send_message(
            chat_id=user_id,
            text="🏠 Asosiy sahifaga qaytarildi!",
            reply_markup=get_menu_buttons()
        )
    except Exception as e:
        await bot.send_message(
            chat_id=user_id,
            text=f"Xatolik yuz berdi: {str(e)}"
        )