import re
import html
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.models import TelegramUser
from bot.selectors import get_user, get_referrer_by_id, get_all_channels
from bot.states import UserRegistrationState
from bot.buttons.default.contact import get_contact as get_phone_keyboard
from bot.buttons.inline.regions import get_region_buttons
from bot.buttons.inline.professions import get_profession_buttons
from bot.buttons.default.gender import get_gender_keyboard
from bot.services import create_user
from bot.constants import REGIONS, PROFESSIONS, GENDER, Messages
from bot.utils import format_phone_number, get_region_code_by_name, get_gender_code_by_name
from bot.buttons.default.menu import get_menu_keyboard
from bot.buttons.inline.age import get_age_button
from bot.buttons.default.back import get_back_keyboard
from bot.selectors import get_user_buy_course, get_all_active_courses

router = Router()

# 🚀 /start
@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user = await get_user(user_id)

    if user:
        if await get_user_buy_course(telegram_id = user_id) == True:
            await message.answer(
                text = Messages.welcome_message.value.format(
                    full_name = user.full_name
                ),
                reply_markup = get_menu_keyboard()
            )
            return
        # Foydalanuvchi kurs sotib olmagan bo‘lsa
        courses = await get_all_active_courses()
        if courses:
            course = courses[0]  # Eng oxirgi faol kurs
            text = (
                f"🎓 <b>{course.name}</b>\n\n"
                f"{course.description}\n\n"
                f"💵 Narxi: <b>{course.price} so'm</b>"
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛒 Sotib olish",
                            callback_data=f"buy_course_{course.id}"
                        )
                    ]
                ]
            )
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

    await message.answer(
        text=Messages.ask_full_name.value,
        reply_markup=get_back_keyboard()
    )
    await state.set_state(UserRegistrationState.GET_FULL_NAME)


# 👤 To'liq ism
@router.message(UserRegistrationState.GET_FULL_NAME)
async def get_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if not (3 <= len(full_name) <= 100):
        await message.answer(text=Messages.full_name_error.value)
        return
    await state.update_data(full_name=full_name)
    # Yangi: Yoshni so'rash
    await message.answer(
        text="Yoshingizni tanlang:",
        reply_markup=get_age_button()
    )
    await state.set_state(UserRegistrationState.GET_AGE)


# 🗓 Yosh (callback)
@router.callback_query(UserRegistrationState.GET_AGE, F.data.startswith("age_"))
async def process_age_callback(callback: types.CallbackQuery, state: FSMContext):
    age_code = callback.data.split("_", 1)[1]
    age_map = {
        "18_24": "18-24",
        "25_34": "25-34",
        "35_44": "35-44",
        "45_plus": "45+"
    }
    age_value = age_map.get(age_code)
    if not age_value:
        await callback.answer(text="Yoshni tanlashda xatolik!", show_alert=True)
        return
    
    await state.update_data(age=age_value)
    
    try:
        await callback.message.edit_text(
            text=f"✅ Yosh: <b>{age_value}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Xabarni tahrirlashda xatolik: {e}")
        await callback.message.answer(
            text=f"✅ Yosh: <b>{age_value}</b>",
            parse_mode="HTML"
        )
    
    await callback.message.answer(
        text=Messages.ask_phone_number.value,
        reply_markup=get_phone_keyboard(text="📞 Telefon raqamni yuborish")
    )
    await state.set_state(UserRegistrationState.GET_PHONE_NUMBER)

# 📱 Telefon raqam (kontakt)
@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.contact)
async def get_phone_contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 📱 Telefon raqam (matn)
@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.text)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone_number = format_phone_number(message.text.strip())
    if not phone_number:
        await message.answer(
            text=Messages.phone_number_error.value,
            reply_markup=get_phone_keyboard(text="📞 Telefon raqamni yuborish")
        )
        return
    await state.update_data(phone_number=phone_number)
    await message.answer(text=Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 🏢 Viloyat tanlash (callback)
@router.callback_query(UserRegistrationState.GET_REGION, F.data.startswith("region_"))
async def process_region_callback(callback: types.CallbackQuery, state: FSMContext):
    region_code = callback.data.split("_", 1)[1]
    region_name = next((name for code, name in REGIONS if code == region_code), None)

    if not region_name:
        await callback.answer(text=Messages.region_error.value, show_alert=True)
        return

    await state.update_data(region=region_name)
    await callback.message.edit_text(
        text=Messages.select_region_success.value.format(region=html.escape(region_name))
    )
    await callback.message.answer(text=Messages.ask_profession.value, reply_markup=get_profession_buttons())
    await state.set_state(UserRegistrationState.GET_PROFESSION)


# 💼 Kasb (callback)
@router.callback_query(UserRegistrationState.GET_PROFESSION, F.data.startswith("profession_"))
async def process_profession_callback(callback: types.CallbackQuery, state: FSMContext):
    profession_code = callback.data.split("_", 1)[1]
    profession_name = next((name for code, name in PROFESSIONS if code == profession_code), None)

    if not profession_name:
        await callback.answer(text=Messages.profession_error.value, show_alert=True)
        return

    await state.update_data(profession=profession_name)
    await callback.message.edit_text(
        text=Messages.select_profession_success.value.format(profession=html.escape(profession_name))
    )
    await callback.message.answer(text=Messages.ask_gender.value, reply_markup=get_gender_keyboard())
    await state.set_state(UserRegistrationState.GET_GENDER)


# 👤 Jins
@router.message(UserRegistrationState.GET_GENDER)
async def get_gender(message: types.Message, state: FSMContext, bot: Bot):
    gender_name = message.text.strip().title()
    gender_code = get_gender_code_by_name(gender_name)

    if not gender_code:
        await message.answer(text=Messages.gender_error.value, reply_markup=get_gender_keyboard())
        return

    data = await state.get_data()
    try:
        new_user = await create_user(
            telegram_id=str(message.from_user.id),
            phone_number=data['phone_number'],
            full_name=data['full_name'],
            telegram_username=message.from_user.username or '',
            profession=data['profession'],
            region=get_region_code_by_name(data['region']),
            gender=gender_code,
            age=data.get('age')  # Yangi: yoshni ham saqlash
        )

        if new_user:
            await message.answer(
                text=Messages.welcome_message_for_registration.value,
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )

            # Registratsiya tugagandan so'ng majburiy kanallarni tekshirish
            await check_channels_after_registration(message, bot)

        else:
            await message.answer(text=Messages.registration_error.value)
    except Exception as e:
        logging.error(f"Registration error for user {message.from_user.id}: {e}")
        await message.answer(text=Messages.system_error.value)
    finally:
        await state.clear()
        
# 📢 Registratsiyadan so'ng majburiy kanallarni tekshirish
async def check_channels_after_registration(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    channels = await get_all_channels()

    if not channels:
        await message.answer(
            text=Messages.welcome_message.value.format(
                full_name=html.escape(message.from_user.full_name or "Foydalanuvchi")
            ),
            reply_markup=get_menu_keyboard()
        )
        return

    not_subscribed_channels = []

    for channel in channels:
        is_telegram = getattr(channel, "is_telegram", True)
        is_private = getattr(channel, "is_private", False)

        if is_telegram and getattr(channel, "telegram_id", None):
            try:
                member = await bot.get_chat_member(
                    chat_id=channel.telegram_id,
                    user_id=user_id
                )
                
                # 'restricted' statusi endi a'zo deb hisoblanadi, shuning uchun faqat 'left' va 'kicked' tekshiriladi.
                if member.status in ['left', 'kicked']:
                    not_subscribed_channels.append(channel)
            
            except TelegramBadRequest as e:
                logging.error(f"Kanal {channel.name} tekshirishda xatolik: {e}")
                not_subscribed_channels.append(channel)
            except TelegramForbiddenError:
                logging.error(f"Bot kanaldan chiqarib yuborilgan yoki unga kira olmaydi: {channel.name}")
                not_subscribed_channels.append(channel)
            except Exception as e:
                logging.error(f"Kutilmagan xatolik: {e}")
                not_subscribed_channels.append(channel)
        else:
            not_subscribed_channels.append(channel)

    if not not_subscribed_channels:
        user = await get_user(message.from_user.id)
        if await get_user_buy_course(telegram_id = user_id) == True:
            
            await message.answer(
                text = Messages.welcome_message.value.format(
                    full_name = user.full_name
                ),
                reply_markup = get_menu_keyboard()
            )
            return
        # Foydalanuvchi kurs sotib olmagan bo‘lsa
        courses = await get_all_active_courses()
        if courses:
            course = courses[0]  # Eng oxirgi faol kurs
            text = (
                f"🎓 <b>{course.name}</b>\n\n"
                f"{course.description}\n\n"
                f"💵 Narxi: <b>{course.price} so'm</b>"
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛒 Sotib olish",
                            callback_data=f"buy_course_{course.id}"
                        )
                    ]
                ]
            )
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
    else:
        # pending_channels argumenti olib tashlandi.
        await send_subscription_message_after_registration(message, not_subscribed_channels)


# 📢 Registratsiyadan so'ng majburiy kanallar xabari
async def send_subscription_message_after_registration(message: types.Message, channels: list):
    text = getattr(Messages.do_member_in_channel, 'value', 
                    "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:")
    
    text += "\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    if channels:
        for channel in channels:
            username = html.escape(channel.name or "Kanal")
            link = getattr(channel, "link", None)
            is_private = getattr(channel, "is_private", False)

            if link:
                button_text = f"🔒 {username}" if is_private else f"📢 {username}"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        url=str(link)
                    )
                ])
                if not is_private:
                    text += f"📢 <b>{username}</b>\n"
                else:
                    text += f"🔒 <b>{username}</b>\n" # pending holati haqida matn olib tashlandi
            else:
                text += f"📢 <b>{username}</b>\n"

    # Pending kanallar haqidagi matn olib tashlandi
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text="✅ A'zolikni tekshirish",
            callback_data="check_subscription"
        )
    ])

    text += "\n💡 <b>A'zo bo'lgandan so'ng A'zolikni tekshirish tugmasini bosing!</b>"

    try:
        await message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Xabar yuborishda xatolik: {e}")
        await message.answer(
            text=Messages.do_member_in_channel.value,
            parse_mode="HTML"
        )

# 🔔 Referral xabar
async def notify_referrer(referrer_id: str, new_user: TelegramUser):
    try:
        pass
    except Exception as e:
        logging.error(f"Referral notification error: {e}")