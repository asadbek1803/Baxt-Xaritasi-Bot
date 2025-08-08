from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types, Router, F
from asgiref.sync import sync_to_async
from aiogram.types import InputFile, Message
from aiogram import Bot
from datetime import datetime
from core import settings
from aiogram.fsm.context import FSMContext
from bot.models import (
    TelegramUser,
    MandatoryChannel,
    Konkurslar,
    Payments
    
)
from bot.selectors import (
    get_active_konkurslar,
    get_konkurs_details,
    create_payment_request,
    get_konkurs_participants_count,
    get_all_admins as get_admin_users
)
router = Router()

# Async database functions

async def notify_admins_about_payment(payment, user, bot):
    admins = await get_admin_users()
    
    for admin in admins:
        try:
            await bot.send_photo(
                chat_id=admin.telegram_id,
                photo=InputFile(payment.payment_screenshot.path),
                caption=(
                    f"🆕 Yangi to'lov so'rovi!\n\n"
                    f"👤 Foydalanuvchi: {user.full_name} (@{user.username if user.username else 'N/A'})\n"
                    f"🏆 Konkurs: {payment.konkurs.title}\n"
                    f"💵 Miqdor: {payment.amount} so'm\n\n"
                    f"🆔 ID: {payment.id}"
                )
            )
        except Exception as e:
            print(f"Adminga xabar yuborishda xatolik: {e}")

# Handlers
@router.message(F.text == "🎉 Konkurslar")
async def handle_konkurslar(message: Message, bot: Bot):
    konkurslar = await get_active_konkurslar()
    
    if not konkurslar:
        await message.answer(
            "Hozircha faol konkurslar mavjud emas. Iltimos, keyinroq qaytib keling.",
            reply_markup=None
        )
        return
    
    builder = InlineKeyboardBuilder()
    
    for konkurs in konkurslar:
        participants_count = await sync_to_async(konkurs.get_participants_count)()
        builder.row(
            types.InlineKeyboardButton(
                text=f"{konkurs.title} ({konkurs.price} so'm) - {participants_count} ishtirokchi",
                callback_data=f"konkurs_{konkurs.id}"
            )
        )
    
    await message.answer(
        "🏆 Mavjud konkurslar ro'yxati:\n\n"
        "Quyidagi konkurslardan birini tanlang:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("konkurs_"))
async def show_konkurs_details(callback: types.CallbackQuery, state: FSMContext):
    konkurs_id = callback.data.split("_")[1]
    konkurs = await get_konkurs_details(konkurs_id)
    
    if not konkurs:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return
    
    participants_count = await sync_to_async(konkurs.get_participants_count)()
    is_full = await sync_to_async(konkurs.is_full)()
    
    details = (
        f"🏆 <b>{konkurs.title}</b>\n\n"
        f"📝 <i>{konkurs.description}</i>\n\n"
        f"💵 Narxi: <b>{konkurs.price} so'm</b>\n"
        f"📅 Boshlanish: <b>{konkurs.start_date.strftime('%d.%m.%Y')}</b>\n"
        f"📅 Tugash: <b>{konkurs.end_date.strftime('%d.%m.%Y')}</b>\n"
        f"👥 Ishtirokchilar: <b>{participants_count}"
        f"{f'/{konkurs.max_participants}' if konkurs.max_participants else ''}</b>\n"
        f"🏆 G'oliblar soni: <b>{konkurs.winner_count}</b>\n"
        f"🔹 Holat: <b>{'Toʻla' if is_full else 'Qabul qilinmoqda'}</b>\n\n"
        f"ℹ️ Konkursda ishtirok etish uchun quyidagi tugma orqali to'lov qiling:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="💳 To'lov qilish",
            callback_data=f"pay_konkurs_{konkurs.id}"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="back_to_konkurs_list"
        )
    )
    
    await callback.message.edit_text(
        details,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_konkurs_list")
async def back_to_list(callback: types.CallbackQuery):
    await handle_konkurslar(callback.message, callback.bot)

@router.callback_query(F.data.startswith("pay_konkurs_"))
async def initiate_payment(callback: types.CallbackQuery, state: FSMContext):
    konkurs_id = callback.data.split("_")[2]
    konkurs = await get_konkurs_details(konkurs_id)
    
    if not konkurs:
        await callback.answer("Konkurs topilmadi!", show_alert=True)
        return
    
    is_full = await sync_to_async(konkurs.is_full)()
    if is_full:
        await callback.answer("⚠️ Bu konkurs uchun barcha joylar band qilingan!", show_alert=True)
        return
    
    await state.update_data(
        konkurs_id=konkurs.id,
        amount=float(konkurs.price)
    )
    
    await callback.message.answer(
        f"💰 <b>To'lov amaliyoti</b>\n\n"
        f"Konkurs: <b>{konkurs.title}</b>\n"
        f"To'lov miqdori: <b>{konkurs.price} so'm</b>\n\n"
        f"1. Quyidagi karta raqamiga to'lov qiling:\n"
        f"<code>8600 1234 5678 9012</code>\n\n"
        f"2. To'lov qilganingizdan so'ng, chek skrinshotini shu yerga yuboring.\n\n"
        f"ℹ️ To'lovni tasdiqlash uchun 1 soat vaqt ketadi.",
        parse_mode="HTML"
    )
    
    await callback.answer()

@router.message(F.photo)
async def handle_payment_screenshot(message: Message, state: FSMContext, bot: Bot):
    project_path = settings.MEDIA_ROOT
    data = await state.get_data()
    if 'konkurs_id' not in data:
        return

    konkurs_id = data['konkurs_id']
    amount = data['amount']
    photo_file_id = message.photo[-1].file_id

    # Skrinshotni yuklab olamiz
    photo_file = await bot.get_file(photo_file_id)
    photo_path = f"{project_path}/{message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    await bot.download_file(photo_file.file_path, photo_path)
    
    # To'lov so'rovini yaratamiz
    payment = await create_payment_request(
        str(message.from_user.id),
        konkurs_id,
        amount,
        photo_path
    )
    
    if payment:
        await message.answer(
            "✅ To'lov so'rovingiz qabul qilindi!\n\n"
            "Admin tomonidan tekshirilgandan so'ng konkursda ishtirok etishingiz mumkin bo'ladi.\n"
            "Tasdiqlash haqida sizga xabar beramiz.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Adminlarga bildirishnoma yuborish
        await notify_admins_about_payment(payment, message.from_user, bot)
    else:
        await message.answer(
            "❌ To'lov so'rovi yaratishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )
    
    await state.clear()