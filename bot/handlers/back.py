from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.constants import Button
from bot.buttons.default.menu import get_menu_keyboard as get_menu_buttons
from bot.selectors import get_user


router = Router()


@router.message(F.text == Button.back.value)
async def handle_back_button(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    try:
        await bot.send_message(
            chat_id=user_id,
            text="🏠 Asosiy sahifaga qaytarildi!",
            reply_markup=get_menu_buttons(),
        )
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=f"Xatolik yuz berdi: {str(e)}")


@router.callback_query(F.data == "back_to_home")
async def back_to_home(callback: types.CallbackQuery):
    """
    Asosiy menyuga qaytish
    """
    await callback.message.delete()
    user_id = str(callback.from_user.id)

    # Foydalanuvchini olish
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi")
        return

    # Inline keyboard yaratish
    InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")]
        ]
    )

    await callback.message.answer(
        "🏠 Asosiy menyu", reply_markup=get_menu_buttons(), parse_mode="HTML"
    )
