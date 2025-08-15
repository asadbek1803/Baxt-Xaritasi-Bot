import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from bot.selectors import get_course_by_user_level, get_user_level, get_user_purchased_courses_with_levels
from bot.states import UserRegistrationState
from bot.constants import Messages, REGIONS, PROFESSIONS, Button
from bot.buttons.inline.age import get_age_button
from bot.buttons.default.contact import get_contact as get_phone_keyboard
from bot.buttons.inline.regions import get_region_buttons
from bot.buttons.inline.professions import get_profession_buttons
from bot.buttons.default.gender import get_gender_keyboard
from bot.utils.formatters import format_phone_number
from bot.utils.helpers import get_region_code_by_name, get_gender_code_by_name
from bot.services.user import create_user, get_user_by_referral_code
from bot.services.subscribe import check_channels_after_registration
from bot.buttons.inline.stages import get_stages_keyboard
router = Router()


# 0. Check if user has username before starting registration
@router.message(UserRegistrationState.GET_FULL_NAME)
async def check_username_before_registration(message: types.Message, state: FSMContext):
    if not message.from_user.username:
        await message.answer("❌ Iltimos, avval Telegram profilingizga username qo'ying!")
        return
    
    full_name = message.text.strip()
    if not (3 <= len(full_name) <= 100):
        await message.answer(Messages.full_name_error.value)
        return

    await state.update_data(full_name=full_name)
    
    # Skip card information and go directly to age selection
    await message.answer("Yoshingizni tanlang:", reply_markup=get_age_button())
    await state.set_state(UserRegistrationState.GET_AGE)


# 1. Yoshni olish
@router.callback_query(UserRegistrationState.GET_AGE, F.data.startswith("age_"))
async def process_age_callback(callback: types.CallbackQuery, state: FSMContext):
    age_map = {"18_24": "18-24", "25_34": "25-34", "35_44": "35-44", "45_plus": "45+"}
    age_value = age_map.get(callback.data.split("_", 1)[1])
    if not age_value:
        await callback.answer("Yoshni tanlashda xatolik!", show_alert=True)
        return

    await state.update_data(age=age_value)

    try:
        await callback.message.edit_text(
            f"✅ Yosh: <b>{age_value}</b>",
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception as e:
        logging.warning(f"Edit text failed: {e}")
        await callback.message.answer(f"✅ Yosh: <b>{age_value}</b>", parse_mode="HTML")

    await callback.answer()
    await callback.message.answer(
        Messages.ask_phone_number.value,
        reply_markup=get_phone_keyboard(text=Button.send_phone_number.value),
    )
    await state.set_state(UserRegistrationState.GET_PHONE_NUMBER)


# 2. Telefon raqamini olish (contact)
@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.contact)
async def get_phone_contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 3. Telefon raqamini olish (matn)
@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.text)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone_number = format_phone_number(message.text.strip())
    if not phone_number:
        await message.answer(
            Messages.phone_number_error.value,
            reply_markup=get_phone_keyboard(text=Button.send_phone_number.value),
        )
        return
    await state.update_data(phone_number=phone_number)
    await message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 4. Region tanlash
@router.callback_query(UserRegistrationState.GET_REGION, F.data.startswith("region_"))
async def process_region_callback(callback: types.CallbackQuery, state: FSMContext):
    region_code = callback.data.split("_", 1)[1]
    region_name = next((name for code, name in REGIONS if code == region_code), None)
    if not region_name:
        await callback.answer(Messages.region_error.value, show_alert=True)
        return

    await state.update_data(region=region_name)

    try:
        await callback.message.edit_text(
            Messages.select_region_success.value.format(region=region_name),
            reply_markup=None,
        )
    except Exception as e:
        logging.warning(f"Edit text failed: {e}")
        await callback.message.answer(
            Messages.select_region_success.value.format(region=region_name)
        )

    await callback.answer()
    await callback.message.answer(
        Messages.ask_profession.value, reply_markup=get_profession_buttons()
    )
    await state.set_state(UserRegistrationState.GET_PROFESSION)


# 5. Kasb tanlash
@router.callback_query(UserRegistrationState.GET_PROFESSION, F.data.startswith("profession_"))
async def process_profession_callback(callback: types.CallbackQuery, state: FSMContext):
    profession_code = callback.data.split("_", 1)[1]
    profession_name = next(
        (name for code, name in PROFESSIONS if code == profession_code), None
    )
    if not profession_name:
        await callback.answer(Messages.profession_error.value, show_alert=True)
        return

    await state.update_data(profession=profession_name)

    try:
        await callback.message.edit_text(
            Messages.select_profession_success.value.format(profession=profession_name),
            reply_markup=None,
        )
    except Exception as e:
        logging.warning(f"Edit text failed: {e}")
        await callback.message.answer(
            Messages.select_profession_success.value.format(profession=profession_name)
        )

    await callback.answer()
    await callback.message.answer(
        Messages.ask_gender.value, reply_markup=get_gender_keyboard()
    )
    await state.set_state(UserRegistrationState.GET_GENDER)


# 6. Jins tanlash va foydalanuvchini yaratish
@router.message(UserRegistrationState.GET_GENDER)
async def get_gender(message: types.Message, state: FSMContext, bot: Bot):
    gender_name = message.text.strip().title()
    gender_code = get_gender_code_by_name(gender_name)
    user_id = message.from_user.id
    
    if not gender_code:
        await message.answer(
            Messages.gender_error.value, reply_markup=get_gender_keyboard()
        )
        return

    data = await state.get_data()

    # Check username again before completing registration
    if not message.from_user.username:
        await message.answer("❌ Iltimos, avval Telegram profilingizga username qo'ying!")
        return

    referral_code = data.get("referral_code", None)
    invited_by_user = None

    if referral_code:
        try:
            invited_by_user = await get_user_by_referral_code(referral_code)
        except Exception as e:
            logging.error(f"Error finding referrer: {e}")

    try:
        user = await create_user(
            telegram_id=str(message.from_user.id),
            phone_number=data["phone_number"],
            full_name=data["full_name"],
            telegram_username=message.from_user.username,
            profession=data["profession"],
            region=get_region_code_by_name(data["region"]),
            gender=gender_code,
            referral_code=None,
            invited_by=invited_by_user,
            age=data.get("age"),
            # Removed card_number and card_holder_name fields
        )

        if not user:
            await message.answer(Messages.system_error.value)
            return

        referral_message = ""
        if invited_by_user:
            referral_message = f"\n\n🎉 Siz {invited_by_user.full_name} tomonidan taklif qilindingiz!"

        user_level = await get_user_level(telegram_id=user_id)
        course = await get_course_by_user_level(user_level)
        price_formatted = "{:,}".format(course.price)
        purchased_course_levels = await get_user_purchased_courses_with_levels(user_id)

        await message.answer(
            Messages.welcome_message_for_registration.value.format(price_formatted) + referral_message,
            parse_mode="HTML",
            reply_markup=get_stages_keyboard(user_level, purchased_course_levels, False)
        )

    except Exception as e:
        logging.error(f"Registration error: {e}", exc_info=True)
        await message.answer(Messages.system_error.value)
    finally:
        await state.clear()