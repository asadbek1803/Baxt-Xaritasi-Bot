import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
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
from bot.handlers.stages import get_stages_keyboard
from bot.selectors import get_all_channels


router = Router()


# 1. Ism familya olish
@router.message(UserRegistrationState.GET_FULL_NAME)
async def get_full_name(message: types.Message, state: FSMContext):
    if not message.from_user.username:
        await message.answer("❌ Iltimos, avval Telegram profilingizga username qo'ying!")
        return
    
    full_name = message.text.strip()
    if not (3 <= len(full_name) <= 100):
        await message.answer(Messages.full_name_error.value)
        return

    await state.update_data(full_name=full_name)
    await message.answer(
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
    await message.answer(
        Messages.ask_gender.value, 
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(UserRegistrationState.GET_GENDER)


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
    await message.answer(
        Messages.ask_gender.value, 
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(UserRegistrationState.GET_GENDER)


# 4. Jins tanlash
@router.message(UserRegistrationState.GET_GENDER)
async def get_gender(message: types.Message, state: FSMContext):
    gender_name = message.text.strip().title()
    gender_code = get_gender_code_by_name(gender_name)
    
    if not gender_code:
        await message.answer(
            Messages.gender_error.value, 
            reply_markup=get_gender_keyboard()
        )
        return

    await state.update_data(gender=gender_code)
    await message.answer("Yoshingizni tanlang:", reply_markup=get_age_button())
    await state.set_state(UserRegistrationState.GET_AGE)


# 5. Yoshni olish
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
    await callback.message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 6. Manzil (Region) tanlash
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


@router.callback_query(UserRegistrationState.GET_PROFESSION, F.data.startswith("profession_"))
async def process_profession_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    # 1. Verify user has username
    if not callback.from_user.username:
        await callback.answer("❌ Iltimos, avval Telegram profilingizga username qo'ying!", show_alert=True)
        return

    # 2. Process profession selection
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

    # 3. Complete registration with proper checks
    await complete_registration(callback.message, state, callback.from_user.id, callback.from_user.username)


async def complete_registration(message: types.Message, state: FSMContext, user_id: int, username: str):
    # 1. Final username check
    if not username:
        await message.answer("❌ Iltimos, avval Telegram profilingizga username qo'ying!")
        return

    data = await state.get_data()

    # 2. Process referral code if exists
    referral_code = data.get("referral_code", None)
    invited_by_user = None

    if referral_code:
        try:
            invited_by_user = await get_user_by_referral_code(referral_code)
        except Exception as e:
            logging.error(f"Error finding referrer: {e}")

    try:
        # 3. Create user in database
        user = await create_user(
            telegram_id=str(user_id),
            phone_number=data["phone_number"],
            full_name=data["full_name"],
            telegram_username=username,
            profession=data["profession"],
            region=get_region_code_by_name(data["region"]),
            gender=data["gender"],
            referral_code=None,
            invited_by=invited_by_user,
            level="level_0",
            age=data.get("age"),
        )

        if not user:
            await message.answer(Messages.system_error.value)
            return

        # 4. Prepare referral message if applicable
        referral_message = ""
        if invited_by_user:
            referral_message = f"\n\n🎉 Siz {invited_by_user.full_name} tomonidan taklif qilindingiz!"

        # 5. Clear state before proceeding
        await state.clear()

        # 6. Verify subscription before showing content
        await verify_and_show_content(message, user_id, referral_message)

    except Exception as e:
        logging.error(f"Registration error: {e}", exc_info=True)
        await message.answer(Messages.system_error.value)


async def verify_and_show_content(message: types.Message, user_id: int, referral_message: str = ""):
    """Verify subscription and show appropriate content using middleware logic"""
    try:
        # Get all channels
        channels = await get_all_channels()
        if not channels:
            await show_stages_content(message, user_id, referral_message)
            return

        # Separate telegram and other channels
        telegram_channels = [ch for ch in channels if ch.is_telegram]
        other_channels = [ch for ch in channels if not ch.is_telegram]

        # Check subscription status using middleware-style checking
        not_subscribed = await check_subscription_status(message.bot, user_id, telegram_channels)

        if not_subscribed:
            # Show subscription request with the same format as middleware
            await show_subscription_request(
                message,
                not_subscribed_telegram_channels=not_subscribed,
                other_channels=other_channels,
                referral_message=referral_message
            )
        else:
            # Show stages content
            await show_stages_content(message, user_id, referral_message)
    except Exception as e:
        logging.error(f"Error in verify_and_show_content: {e}")
        await message.answer(Messages.system_error.value)


async def check_subscription_status(bot: Bot, user_id: int, channels: list) -> list:
    """Check which channels user is not subscribed to (middleware-style)"""
    not_subscribed = []

    for channel in channels:
        try:
            # Try both telegram_id and link as identifier
            chat_identifier = None
            if channel.telegram_id:
                chat_identifier = channel.telegram_id
            elif channel.link and channel.link.startswith("https://t.me/"):
                chat_identifier = f"@{channel.link.split('/')[-1]}"

            if not chat_identifier:
                logging.warning(f"No valid identifier for channel {channel.name}")
                not_subscribed.append(channel)
                continue

            # Check membership status
            member = await bot.get_chat_member(chat_id=chat_identifier, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel)

        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logging.warning(f"Subscription check failed for {channel.name}: {e}")
            not_subscribed.append(channel)
        except Exception as e:
            logging.error(f"Unexpected error checking channel {channel.name}: {e}")
            not_subscribed.append(channel)

    return not_subscribed


async def show_subscription_request(
    message: types.Message,
    not_subscribed_telegram_channels: list,
    other_channels: list = None,
    referral_message: str = ""
):
    """Show subscription request with same format as middleware"""
    if other_channels is None:
        other_channels = []

    try:
        text = "🎉 Registratsiya muvaffaqiyatli yakunlandi!" + referral_message
        text += "\n\n📢 Botdan to'liq foydalanish uchun quyidagi majburiy kanallarga a'zo bo'ling:\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        # Majburiy Telegram kanallar
        for channel in not_subscribed_telegram_channels:
            channel_name = channel.name
            button_text = f"📢 {channel_name}"

            if channel.link:
                keyboard.inline_keyboard.append(
                    [InlineKeyboardButton(text=button_text, url=channel.link)]
                )
                text += f"{button_text}\n"

        # Qo'shimcha kanallar
        if other_channels:
            text += "\n🌐 Qo'shimcha homiy kanallar:\n"
            for channel in other_channels:
                channel_name = channel.name
                button_text = f"🌐 {channel_name}"

                if channel.link:
                    keyboard.inline_keyboard.append(
                        [InlineKeyboardButton(text=button_text, url=channel.link)]
                    )
                    text += f"{button_text}\n"

        # Tekshirish tugmasi
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="✅ A'zolikni tekshirish",
                callback_data="check_subscription"
            )
        ])

        text += "\n💡 <b>Majburiy kanallarga a'zo bo'lgandan so'ng tekshirish tugmasini bosing!</b>"

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Error showing subscription request: {e}")
        await message.answer(
            "📢 Botdan foydalanish uchun majburiy kanallarga a'zo bo'ling!",
            parse_mode="HTML"
        )


async def show_stages_content(message: types.Message, user_id: int, referral_message: str = ""):
    """Show stages content after verification"""
    user_level = await get_user_level(telegram_id=user_id)
    purchased_course_levels = await get_user_purchased_courses_with_levels(user_id)
    course = await get_course_by_user_level(user_level)
    price_formatted = "{:,}".format(course.price)

    text = "🎉 Registratsiya muvaffaqiyatli yakunlandi!" + referral_message
    text += f"\n\n{Messages.welcome_message_for_registration.value.format(price_formatted)}"
    text += "\n\n🚀 Endi kurslarimiz bilan tanishing:"

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_stages_keyboard(
            user_level=user_level,
            purchased_course_levels=purchased_course_levels
        )
    )