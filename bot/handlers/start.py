import re
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

from bot.models import TelegramUser
from bot.selectors import get_user, get_referrer_by_id
from bot.states import UserRegistrationState
from bot.buttons.default.contact import get_contact as get_phone_keyboard
from bot.buttons.inline.regions import get_region_buttons
from bot.buttons.inline.professions import get_profession_buttons
from bot.buttons.default.gender import get_gender_keyboard
from bot.services import create_user
from bot.constants import REGIONS, PROFESSIONS, GENDER
from bot.functions import format_phone_number, get_region_code_by_name, get_gender_code_by_name

router = Router()



    

# 🚀 /start
@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user = await get_user(user_id)

    if user:
        await message.answer(
            f"Salom, {user.first_name}! Siz allaqachon ro'yxatdan o'tgansiz.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return

    # Referral uchun joy qoldirilgan (ixtiyoriy)
    # command_args = message.text.split()
    # if len(command_args) > 1:
    #     referral_code = command_args[1]
    #     referrer = await get_referrer_by_id(referral_code)
    #     if referrer:
    #         await state.update_data(referrer_id=referrer.telegram_id)

    await message.answer(
        "🎉 Xush kelibsiz!\nRo'yxatdan o'tish uchun ismingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(UserRegistrationState.GET_FIRST_NAME)


# 👤 Ism
@router.message(UserRegistrationState.GET_FIRST_NAME)
async def get_first_name(message: types.Message, state: FSMContext):
    first_name = message.text.strip()
    if not (2 <= len(first_name) <= 50):
        await message.answer("❌ Ism 2-50 ta belgi orasida bo'lishi kerak. Qaytadan kiriting:")
        return
    await state.update_data(first_name=first_name)
    await message.answer("Endi familiyangizni kiriting:")
    await state.set_state(UserRegistrationState.GET_LAST_NAME)


# 👤 Familiya
@router.message(UserRegistrationState.GET_LAST_NAME)
async def get_last_name(message: types.Message, state: FSMContext):
    last_name = message.text.strip()
    if not (2 <= len(last_name) <= 50):
        await message.answer("❌ Familiya 2-50 ta belgi orasida bo'lishi kerak. Qaytadan kiriting:")
        return
    await state.update_data(last_name=last_name)
    await message.answer(
        "📱 Telefon raqamingizni yuboring:",
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
    await message.answer("🏢 Viloyatingizni tanlang:", reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 📱 Telefon raqam (matn)
@router.message(UserRegistrationState.GET_PHONE_NUMBER, F.text)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone_number = format_phone_number(message.text.strip())
    if not phone_number:
        await message.answer(
            "❌ Telefon raqam noto'g'ri formatda!\n"
            "Iltimos, tugmani bosing yoki +998901234567 formatida kiriting:",
            reply_markup=get_phone_keyboard(text="📞 Telefon raqamni yuborish")
        )
        return
    await state.update_data(phone_number=phone_number)
    await message.answer("🏢 Viloyatingizni tanlang:", reply_markup=get_region_buttons())
    await state.set_state(UserRegistrationState.GET_REGION)


# 🏢 Viloyat tanlash (callback)
@router.callback_query(UserRegistrationState.GET_REGION, F.data.startswith("region_"))
async def process_region_callback(callback: types.CallbackQuery, state: FSMContext):
    region_code = callback.data.split("_", 1)[1]
    region_name = next((name for code, name in REGIONS if code == region_code), None)

    if not region_name:
        await callback.answer("❌ Noto‘g‘ri tanlov!", show_alert=True)
        return

    await state.update_data(region=region_name)
    await callback.message.edit_text(f"✅ Siz {region_name} viloyatini tanladingiz.")
    await callback.message.answer("🎂 Yoshingizni kiriting (raqam bilan):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(UserRegistrationState.GET_AGE)

# 🎂 Yosh
@router.message(UserRegistrationState.GET_AGE)
async def get_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if not (16 <= age <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❌ Yosh 16-100 orasida bo'lishi kerak. Qaytadan kiriting:")
        return
    await state.update_data(age=age)
    await message.answer("💼 Kasbingizni tanlang:", reply_markup=get_profession_buttons())
    await state.set_state(UserRegistrationState.GET_PROFESSION)


# 💼 Kasb (callback)
@router.callback_query(UserRegistrationState.GET_PROFESSION, F.data.startswith("profession_"))
async def process_profession_callback(callback: types.CallbackQuery, state: FSMContext):
    profession_code = callback.data.split("_", 1)[1]
    profession_name = None

    for code, name in PROFESSIONS:
        if code == profession_code:
            profession_name = name
            break

    if not profession_name:
        await callback.answer("❌ Noto‘g‘ri tanlov!", show_alert=True)
        return

    await state.update_data(profession=profession_name)
    await callback.message.edit_text(f"✅ Siz {profession_name} kasbini tanladingiz.")
    await callback.message.answer("👤 Jinsingizni tanlang:", reply_markup=get_gender_keyboard())
    await state.set_state(UserRegistrationState.GET_GENDER)


# 👤 Jins
@router.message(UserRegistrationState.GET_GENDER)
async def get_gender(message: types.Message, state: FSMContext):
    gender = message.text.strip().title()
    if gender not in ["Erkak", "Ayol"]:
        await message.answer("❌ Iltimos, jinsingizni tanlang:", reply_markup=get_gender_keyboard())
        return

    data = await state.get_data()
    print(f"Region: {data.get('region')}, Profession: {data.get('profession')}")
    try:

        new_user = await create_user(
            telegram_id=str(message.from_user.id),
            phone_number=data['phone_number'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            telegram_username=message.from_user.username or '',
            age=data['age'],
            profession=data['profession'],
            region=get_region_code_by_name(data['region']),
            gender=get_gender_code_by_name(message.text)
        )

        if new_user:
            await message.answer(
                f"🎉 Ro'yxatdan o'tish muvaffaqiyatli yakunlandi, {new_user.first_name}!\n"
                "Siz endi botimizning barcha funksiyalaridan foydalanishingiz mumkin.",
                reply_markup=ReplyKeyboardRemove()
            )

            # if new_user.referrer:
            #     await notify_referrer(new_user.referrer, new_user)
        else:
            await message.answer("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
    except Exception as e:
        print(f"Registration error: {e}")
        await message.answer("❌ Tizimda xatolik yuz berdi. Keyinroq urinib ko'ring.")
    finally:
        await state.clear()


# 🔔 Referral xabar
async def notify_referrer(referrer_id: str, new_user: TelegramUser):
    try:
        # Referral logikasi shu yerda bo'ladi
        pass
    except Exception as e:
        print(f"Notification error: {e}")
