import logging

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.selectors import (
    get_user,
    check_user_referral_code,
    get_user_buy_course,
    get_user_level,
)
from bot.states import UserRegistrationState
from bot.services.registration import send_course_offer
from bot.constants import Messages
from bot.buttons.default.menu import get_menu_keyboard

router = Router()


@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)

    # Extract referral code from /start command
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None
    referral_user = None

    if referral_code:
        try:
            referral_user = await check_user_referral_code(referral_code)
            if referral_user:
                # State-ga ikkala nom bilan ham saqlash (eski va yangi)
                await state.update_data(
                    referral_code=referral_code,
                    invited_by=referral_user,
                    # Eski nomlar ham (backward compatibility uchun)
                    refferal_code=referral_code,
                    refferal_user=referral_user,
                )

                await message.answer(
                    text=(
                        "📝 Referral tarqatuvchi ma'lumotlari topildi ✅\n\n"
                        f"👤 <b>Foydalanuvchi:</b> {referral_user.full_name}\n"
                        f"🔗 <b>Referal kod:</b> <code>{referral_user.referral_code}</code>\n"
                        f"🎓 <b>Referal darajasi:</b> {referral_user.level}\n"
                        f"🆔 <b>Referal ID:</b> <code>{referral_user.telegram_id}</code>"
                    ),
                    parse_mode="HTML",
                )
                logging.info(
                    f"Valid referral code found: {referral_code} from user {referral_user.full_name}"
                )
            else:
                await message.answer(
                    "⚠️ Berilgan referal kod noto'g'ri. Iltimos, to'g'ri referal kodni kiriting."
                )
                logging.warning(f"Invalid referral code: {referral_code}")
                return
        except Exception as e:
            logging.error(f"Error checking referral code {referral_code}: {e}")
            await message.answer("⚠️ Referal kodini tekshirishda xatolik yuz berdi.")
            return

    if not user:
        # Only allow registration if referral code is present
        if not referral_code:
            await message.answer(
                "⚠️ Botdan faqat referal kod bilan foydalana olasiz. "
                "Sizda u yo'q bo'lsa @adminusernamega murojjat qiling!"
            )
            return

        # Referral ma'lumotlarini log qilish
        if referral_user:
            logging.info(
                f"Starting registration with referrer: {referral_user.full_name} (code: {referral_code})"
            )

        await message.answer(
            Messages.ask_full_name.value
        )
        await state.set_state(UserRegistrationState.GET_FULL_NAME)
        return

    user_level = await get_user_level(telegram_id=user_id)

    # Agar foydalanuvchi birinchi bosqichda bo'lsa
    if user_level == "0-bosqich":
        has_course = await get_user_buy_course(user_id)

        if has_course:
            # Agar kurs sotib olingan bo'lsa → menyu
            await message.answer(
                text=Messages.welcome_message.value.format(full_name=user.full_name),
                reply_markup=get_menu_keyboard(),
            )
        else:
            # Agar kurs sotib olinmagan bo'lsa → kurs taklif qilinadi
            await send_course_offer(message)
        return

    # Agar foydalanuvchi yuqori bosqichda bo'lsa → menyu
    await message.answer(
        text=Messages.welcome_message.value.format(full_name=user.full_name),
        reply_markup=get_menu_keyboard(),
    )
