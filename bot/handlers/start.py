from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bot.selectors import get_user, get_user_buy_course, get_user_level
from bot.states import UserRegistrationState
from bot.services.registration import send_course_offer
from bot.constants import Messages
from bot.buttons.default.back import get_back_keyboard
from bot.buttons.default.menu import get_menu_keyboard

router = Router()

@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user:
        user_level = await get_user_level(telegram_id=user_id)

        # Agar foydalanuvchi birinchi bosqichda bo'lsa
        if user_level == "1-bosqich":
            has_course = await get_user_buy_course(user_id)

            if has_course:
                # Agar kurs sotib olingan bo‘lsa → menyu
                await message.answer(
                    text=Messages.welcome_message.value.format(full_name=user.full_name),
                    reply_markup=get_menu_keyboard()
                )
            else:
                # Agar kurs sotib olinmagan bo‘lsa → kurs taklif qilinadi
                await send_course_offer(message)
            return

        # Agar foydalanuvchi yuqori bosqichda bo‘lsa → menyu
        await message.answer(
            text=Messages.welcome_message.value.format(full_name=user.full_name),
            reply_markup=get_menu_keyboard()
        )
        return

    # Agar foydalanuvchi mavjud bo‘lmasa → ro‘yxatdan o‘tish
    await message.answer(Messages.ask_full_name.value, reply_markup=get_back_keyboard())
    await state.set_state(UserRegistrationState.GET_FULL_NAME)
