from aiogram import types, F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import TelegramUser
from bot.handlers.my_profile import my_profile_handler
from bot.selectors import fetch_user, update_user_card_info
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.buttons.default.back import get_back_keyboard
router = Router()

class CardInfoStates(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_card_holder_name = State()


@router.callback_query(F.data.startswith("card_info_"))
async def show_card_info(callback: types.CallbackQuery):
    """Plastik karta ma'lumotlarini ko'rsatish va tahrirlash"""
    try:
        user_id = callback.data.split("_")[2]
        user_info = await fetch_user(user_id)
        
        if not user_info:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
        
        # Karta ma'lumotlarini formatlash
        card_number = user_info.card_number if user_info.card_number else "Kiritilmagan"
        card_holder = user_info.card_holder_full_name if user_info.card_holder_full_name else "Kiritilmagan"
        
        # Karta raqamini maskirovka qilish (agar mavjud bo'lsa)
        if user_info.card_number and len(user_info.card_number) >= 4:
            masked_card = "*" * (len(user_info.card_number) - 4) + user_info.card_number[-4:]
        else:
            masked_card = card_number
        
        card_info_text = (
            f"💳 <b>Plastik karta ma'lumotlari</b>\n\n"
            f"🔢 Karta raqami: <code>{masked_card}</code>\n"
            f"👤 Karta egasi: <b>{card_holder}</b>\n\n"
            f"💡 <i>Bu ma'lumotlar to'lovlar uchun ishlatiladi</i>"
        )
        
        # Tugmalar yaratish
        builder = InlineKeyboardBuilder()
        
        if user_info.card_number and user_info.card_holder_full_name:
            # Agar karta ma'lumotlari mavjud bo'lsa - tahrirlash tugmasi
            builder.row(
                types.InlineKeyboardButton(
                    text="✏️ Karta ma'lumotlarini tahrirlash",
                    callback_data=f"edit_card_{user_id}"
                )
            )
        else:
            # Agar karta ma'lumotlari yo'q bo'lsa - qo'shish tugmasi
            builder.row(
                types.InlineKeyboardButton(
                    text="➕ Karta ma'lumotlarini qo'shish",
                    callback_data=f"add_card_{user_id}"
                )
            )
        
       
        
        await callback.message.edit_text(
            text=card_info_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        
    except Exception as e:
        print(f"Error showing card info: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("add_card_"))
async def start_add_card(callback: types.CallbackQuery, state: FSMContext):
    """Karta ma'lumotlarini qo'shishni boshlash"""
    try:
        user_id = callback.data.split("_")[2]
        
        await state.update_data(user_id=user_id, action="add")
        await state.set_state(CardInfoStates.waiting_for_card_number)
        
        await callback.message.edit_text(
            "💳 <b>Plastik karta raqamini kiriting</b>\n\n"
            "📝 16 raqamli karta raqamingizni kiriting:\n"
            "Masalan: <code>1234567812345678</code>\n\n"
            "❌ Bekor qilish uchun /cancel yozing",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Error starting add card: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data.startswith("edit_card_"))
async def start_edit_card(callback: types.CallbackQuery, state: FSMContext):
    """Karta ma'lumotlarini tahrirlashni boshlash"""
    try:
        user_id = callback.data.split("_")[2]
        
        await state.update_data(user_id=user_id, action="edit")
        await state.set_state(CardInfoStates.waiting_for_card_number)
        
        await callback.message.edit_text(
            "✏️ <b>Yangi karta raqamini kiriting</b>\n\n"
            "📝 16 raqamli yangi karta raqamingizni kiriting:\n"
            "Masalan: <code>1234567812345678</code>\n\n"
            "❌ Bekor qilish uchun /cancel yozing",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Error starting edit card: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.message(CardInfoStates.waiting_for_card_number)
async def process_card_number(message: types.Message, state: FSMContext):
    """Karta raqamini qabul qilish"""
    try:
        card_number = message.text.strip().replace(" ", "").replace("-", "")
        
        # Karta raqami validatsiyasi
        if not card_number.isdigit():
            await message.answer(
                "❌ <b>Xato!</b>\n\n"
                "Karta raqami faqat raqamlardan iborat bo'lishi kerak.\n"
                "Iltimos, qaytadan kiriting:",
                parse_mode="HTML"
            )
            return
        
        if len(card_number) != 16:
            await message.answer(
                "❌ <b>Xato!</b>\n\n"
                "Karta raqami 16 ta raqamdan iborat bo'lishi kerak.\n"
                "Iltimos, qaytadan kiriting:",
                parse_mode="HTML"
            )
            return
        
        # Karta raqamini saqlash va keyingi bosqichga o'tish
        await state.update_data(card_number=card_number)
        await state.set_state(CardInfoStates.waiting_for_card_holder_name)
        
        # Karta raqamini maskirovka qilish
        masked_card = "*" * 12 + card_number[-4:]
        
        await message.answer(
            f"✅ <b>Karta raqami qabul qilindi</b>\n\n"
            f"🔢 Karta: <code>{masked_card}</code>\n\n"
            f"👤 <b>Endi karta egasining to'liq ismini kiriting:</b>\n"
            f"Masalan: <code>ABDULLAYEV AZAMAT AKMAL O'G'LI</code>\n\n"
            f"❌ Bekor qilish uchun /cancel yozing",
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Error processing card number: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@router.message(CardInfoStates.waiting_for_card_holder_name)
async def process_card_holder_name(message: types.Message, state: FSMContext):
    """Karta egasi ismini qabul qilish va saqlash"""
    try:
        card_holder_name = message.text.strip().upper()
        
        # Karta egasi ismi validatsiyasi
        if len(card_holder_name) < 2:
            await message.answer(
                "❌ <b>Xato!</b>\n\n"
                "Karta egasining ismi juda qisqa.\n"
                "Iltimos, to'liq ismni kiriting:",
                parse_mode="HTML"
            )
            return
        
        if len(card_holder_name) > 200:
            await message.answer(
                "❌ <b>Xato!</b>\n\n"
                "Karta egasining ismi juda uzun.\n"
                "Iltimos, qisqaroq ism kiriting:",
                parse_mode="HTML"
            )
            return
        
        # State ma'lumotlarini olish
        data = await state.get_data()
        user_id = data.get('user_id')
        card_number = data.get('card_number')
        action = data.get('action')
        
        # Ma'lumotlarni bazaga saqlash
        success = await update_user_card_info(user_id, card_number, card_holder_name)
        
        if success:
            # Karta raqamini maskirovka qilish
            masked_card = "*" * 12 + card_number[-4:]
            
            action_text = "tahrirlandi" if action == "edit" else "qo'shildi"
            
            await message.answer(
                f"✅ <b>Plastik karta ma'lumotlari muvaffaqiyatli {action_text}!</b>\n\n"
                f"🔢 Karta raqami: <code>{masked_card}</code>\n"
                f"👤 Karta egasi: <b>{card_holder_name}</b>\n\n"
                f"💡 <i>Bu ma'lumotlar xavfsiz saqlanadi va faqat to'lovlar uchun ishlatiladi.</i>",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ma'lumotlarni saqlashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        
        # State-ni tozalash
        await state.clear()
        
    except Exception as e:
        print(f"Error processing card holder name: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        await state.clear()


@router.message(F.text == "/cancel")
async def cancel_card_setup(message: types.Message, state: FSMContext):
    """Karta kiritish jarayonini bekor qilish"""
    current_state = await state.get_state()
    
    if current_state in [CardInfoStates.waiting_for_card_number, CardInfoStates.waiting_for_card_holder_name]:
        await state.clear()
        await message.answer(
            "❌ <b>Plastik karta ma'lumotlarini kiritish bekor qilindi</b>\n\n"
            "📱 Asosiy menyuga qaytish uchun /start tugmasini bosing.",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: types.CallbackQuery):
    """Profil sahifasiga qaytish"""
    try:
        # Profil handler-ini qayta chaqirish
        fake_message = types.Message(
            message_id=callback.message.message_id,
            from_user=callback.from_user,
            date=callback.message.date,
            chat=callback.message.chat,
            content_type="text",
            text="👤 Mening hisobim"
        )
        
        await my_profile_handler(fake_message, callback.bot)
        
    except Exception as e:
        print(f"Error going back to profile: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)