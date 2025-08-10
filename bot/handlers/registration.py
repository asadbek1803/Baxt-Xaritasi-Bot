import html
import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
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

router = Router()

@router.message(UserRegistrationState.GET_FULL_NAME)
async def get_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if not (3 <= len(full_name) <= 100):
        await message.answer(Messages.full_name_error.value)
        return
    await state.update_data(full_name=full_name)
    await message.answer("Yoshingizni tanlang:", reply_markup=get_age_button())
    await state.set_state(UserRegistrationState.GET_AGE)

@router.callback_query(UserRegistrationState.GET_AGE, F.data.startswith("age_"))
async def process_age_callback(callback: types.CallbackQuery, state: FSMContext):
    age_map = {
        "18_24": "18-24", "25_34": "25-34", "35_44": "35-44", "45_plus": "45+"
    }
    age_value = age_map.get(callback.data.split("_", 1)[1])
    if not age_value:
        await callback.answer("Yoshni tanlashda xatolik!", show_alert=True)
        return
    
    await state.update_data(age=age_value)
    
    # Inline keyboard-ni olib tashlash uchun reply_markup=None ishlatamiz
    try:
        await callback.message.edit_text(
            f"✅ Yosh: <b>{age_value}</b>", 
            parse_mode="HTML",
            reply_markup=None  # Bu inline keyboard-ni olib tashlaydi
        )
    except Exception as e:
        # Agar edit_text ishlamasa, yangi xabar yuboramiz
        logging.warning(f"Edit text failed, sending new message: {e}")
        await callback.message.answer(f"✅ Yosh: <b>{age_value}</b>", parse_mode="HTML")
    
    await callback.answer()  # Callback query-ni javoblash
    await callback.message.answer(Messages.ask_phone_number.value, reply_markup=get_phone_keyboard(text = Button.send_phone_number.value))
    await state.set_state(UserRegistrationState.GET_PHONE_NUMBER)

@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.contact)
async def get_phone_contact(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    await state.update_data(phone_number=phone_number)
    await message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)

@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.text)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone_number = format_phone_number(message.text.strip())
    if not phone_number:
        await message.answer(Messages.phone_number_error.value, reply_markup=get_phone_keyboard(text = Button.send_phone_number.value))
        return
    await state.update_data(phone_number=phone_number)
    await message.answer(Messages.ask_region.value, reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)

@router.callback_query(UserRegistrationState.GET_REGION, F.data.startswith("region_"))
async def process_region_callback(callback: types.CallbackQuery, state: FSMContext):
    region_code = callback.data.split("_", 1)[1]
    region_name = next((name for code, name in REGIONS if code == region_code), None)
    if not region_name:
        await callback.answer(Messages.region_error.value, show_alert=True)
        return
    
    await state.update_data(region=region_name)
    
    # Inline keyboard-ni olib tashlash
    try:
        await callback.message.edit_text(
            Messages.select_region_success.value.format(region=html.escape(region_name)),
            reply_markup=None
        )
    except Exception as e:
        logging.warning(f"Edit text failed, sending new message: {e}")
        await callback.message.answer(Messages.select_region_success.value.format(region=html.escape(region_name)))
    
    await callback.answer()
    await callback.message.answer(Messages.ask_profession.value, reply_markup=get_profession_buttons())
    await state.set_state(UserRegistrationState.GET_PROFESSION)

@router.callback_query(UserRegistrationState.GET_PROFESSION, F.data.startswith("profession_"))
async def process_profession_callback(callback: types.CallbackQuery, state: FSMContext):
    profession_code = callback.data.split("_", 1)[1]
    profession_name = next((name for code, name in PROFESSIONS if code == profession_code), None)
    if not profession_name:
        await callback.answer(Messages.profession_error.value, show_alert=True)
        return
    
    await state.update_data(profession=profession_name)
    
    # Inline keyboard-ni olib tashlash
    try:
        await callback.message.edit_text(
            Messages.select_profession_success.value.format(profession=html.escape(profession_name)),
            reply_markup=None
        )
    except Exception as e:
        logging.warning(f"Edit text failed, sending new message: {e}")
        await callback.message.answer(Messages.select_profession_success.value.format(profession=html.escape(profession_name)))
    
    await callback.answer()
    await callback.message.answer(Messages.ask_gender.value, reply_markup=get_gender_keyboard())
    await state.set_state(UserRegistrationState.GET_GENDER)

@router.message(UserRegistrationState.GET_GENDER)
async def get_gender(message: types.Message, state: FSMContext, bot: Bot):
    gender_name = message.text.strip().title()
    gender_code = get_gender_code_by_name(gender_name)
    if not gender_code:
        await message.answer(Messages.gender_error.value, reply_markup=get_gender_keyboard())
        return
    
    data = await state.get_data()
    
    # Referral ma'lumotlarini olish
    referral_code = data.get('referral_code', None)
    invited_by_user = None
    
    # Agar referral code mavjud bo'lsa, taklif qiluvchi foydalanuvchini topamiz
    if referral_code:
        try:
            invited_by_user = await get_user_by_referral_code(referral_code)
            if invited_by_user:
                logging.info(f"Found referrer: {invited_by_user.full_name} for code: {referral_code}")
            else:
                logging.warning(f"Referrer not found for code: {referral_code}")
        except Exception as e:
            logging.error(f"Error finding referrer: {e}")
    
    try:
        user = await create_user(
            telegram_id=str(message.from_user.id),
            phone_number=data['phone_number'],
            full_name=data['full_name'],
            telegram_username=message.from_user.username or '',
            profession=data['profession'],
            region=get_region_code_by_name(data['region']),
            gender=gender_code,
            referral_code=None,  # Bu avtomatik yaratiladi
            invited_by=invited_by_user,  # To'g'ri parametr nomi
            level="0-bosqich",
            age=data.get('age')
        )
        
        if user is None:
            logging.error(f"Failed to create user for telegram_id: {message.from_user.id}")
            await message.answer(Messages.system_error.value)
            return
        
        # Referral xabari
        referral_message = ""
        if invited_by_user:
            referral_message = f"\n\n🎉 Siz {invited_by_user.full_name} tomonidan taklif qilindingiz!"
            
        await message.answer(
            Messages.welcome_message_for_registration.value + referral_message
        )
        await message.answer(
            text="✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        
        
        await check_channels_after_registration(message, bot)
        
    except Exception as e:
        logging.error(f"Registration error: {e}", exc_info=True)
        await message.answer(Messages.system_error.value)
    finally:
        await state.clear()