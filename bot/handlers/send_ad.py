import asyncio
import logging
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.selectors import get_user
from bot.models import TelegramUser
from asgiref.sync import sync_to_async

router = Router()

logger = logging.getLogger(__name__)


@sync_to_async
def get_all_users():
    """Get all active users for advertisement broadcasting"""
    return list(TelegramUser.objects.filter(is_active=True).values_list('telegram_id', flat=True))


@router.message(Command("send_ad"))
async def send_advertisement_command(message: types.Message, state: FSMContext, bot: Bot):
    """
    Handle /send_ad command - allows admin to send advertisements to all users
    """
    user_id = str(message.from_user.id)
    
    # Get user from database
    user = await get_user(user_id)
    
    # Check if user exists and is admin
    if not user:
        await message.reply("⚠️ Siz botda ro'yxatdan o'tmagansiz.")
        return
    
    if not user.is_admin:
        await message.reply("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    # Check if this is a reply to a message (the advertisement content)
    if not message.reply_to_message:
        await message.reply(
            "📢 Reklama yuborish uchun:\n\n"
            "1. Yubormoqchi bo'lgan xabarni yozing\n"
            "2. Shu xabarga javob sifatida /send_ad buyrug'ini yuboring\n\n"
            "⚠️ Barcha foydalanuvchilarga yuboriladi, ehtiyot bo'ling!"
        )
        return
    
    # Get all users
    try:
        all_users = await get_all_users()
        if not all_users:
            await message.reply("⚠️ Hech qanday faol foydalanuvchi topilmadi.")
            return
        
        # Confirm before sending
        await state.update_data(
            ad_message_id=message.reply_to_message.message_id,
            ad_chat_id=message.reply_to_message.chat.id,
            target_users=all_users
        )
        
        ad_preview = (
            message.reply_to_message.text[:100]
            if message.reply_to_message.text
            else '[Media]'
        )
        
        confirm_text = (
            f"📊 Statistika:\n"
            f"👥 Jami foydalanuvchilar: {len(all_users)}\n"
            f"📢 Reklama matn: {ad_preview}...\n\n"
            f"✅ Tasdiqlash uchun: /confirm_ad\n"
            f"❌ Bekor qilish uchun: /cancel_ad"
        )
        
        await message.reply(confirm_text)
        
    except Exception as e:
        logger.error(f"Error preparing advertisement: {e}")
        await message.reply("❌ Reklama tayyorlashda xatolik yuz berdi.")


@router.message(Command("confirm_ad"))
async def confirm_advertisement(message: types.Message, state: FSMContext, bot: Bot):
    """
    Confirm and send advertisement to all users
    """
    user_id = str(message.from_user.id)
    user = await get_user(user_id)
    
    if not user or not user.is_admin:
        await message.reply("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    # Get stored data
    data = await state.get_data()
    if not data or 'ad_message_id' not in data:
        await message.reply(
            "⚠️ Yuborilishi kerak bo'lgan reklama topilmadi. "
            "Iltimos, qaytadan /send_ad buyrug'ini ishlating."
        )
        return
    
    ad_message_id = data['ad_message_id']
    ad_chat_id = data['ad_chat_id']
    target_users = data['target_users']
    
    # Start broadcasting
    status_message = await message.reply("📤 Reklama yuborilmoqda...")
    
    success_count = 0
    failed_count = 0
    
    try:
        for user_telegram_id in target_users:
            try:
                # Copy the message without showing sender info (hides sender name)
                await bot.copy_message(
                    chat_id=user_telegram_id,
                    from_chat_id=ad_chat_id,
                    message_id=ad_message_id,
                    protect_content=False
                )
                success_count += 1
                
                if success_count % 30 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send ad to user {user_telegram_id}: {e}")
                continue
        
        # Update status
        final_text = (
            f"✅ Reklama yuborish yakunlandi!\n\n"
            f"📊 Natijalar:\n"
            f"✅ Muvaffaqiyatli: {success_count}\n"
            f"❌ Muvaffaqiyatsiz: {failed_count}\n"
            f"📈 Umumiy: {len(target_users)}"
        )
        
        await status_message.edit_text(final_text)
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error during advertisement broadcasting: {e}")
        await status_message.edit_text("❌ Reklama yuborishda xatolik yuz berdi.")


@router.message(Command("cancel_ad"))
async def cancel_advertisement(message: types.Message, state: FSMContext):
    """
    Cancel advertisement sending
    """
    user_id = str(message.from_user.id)
    user = await get_user(user_id)
    
    if not user or not user.is_admin:
        await message.reply("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    await state.clear()
    await message.reply("❌ Reklama yuborish bekor qilindi.")

