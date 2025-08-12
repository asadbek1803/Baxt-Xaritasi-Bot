import aiohttp
import asyncio
from datetime import datetime, timedelta
from django.utils import timezone
from core.settings import TELEGRAM_BOT_TOKEN
import logging

# Logger yaratish
logger = logging.getLogger(__name__)

# Bot token

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

class TelegramNotification:
    """Telegram API orqali xabar yuborish uchun klass"""
    
    @staticmethod
    async def send_message(chat_id: str, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = True):
        """
        Telegram API orqali xabar yuborish
        
        Args:
            chat_id: Foydalanuvchi telegram ID
            text: Yuborilishi kerak bo'lgan xabar matni
            parse_mode: Xabar formatlash turi (HTML yoki Markdown)
            disable_web_page_preview: Web preview o'chirish
        
        Returns:
            dict: API javob natijasi
        """
        url = f"{BASE_URL}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        logger.info(f"Message sent successfully to {chat_id}")
                        return {
                            "success": True,
                            "message_id": result["result"]["message_id"],
                            "chat_id": chat_id
                        }
                    else:
                        logger.error(f"Failed to send message to {chat_id}: {result}")
                        return {
                            "success": False,
                            "error": result.get("description", "Unknown error"),
                            "error_code": result.get("error_code")
                        }
                        
        except Exception as e:
            logger.error(f"Exception while sending message to {chat_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def send_referrer_warning(referrer_telegram_id: str, advanced_user_name: str, 
                                   advanced_user_level: str, referrer_level: str):
        """
        Referrerga ogohlantirish xabarini yuborish
        
        Args:
            referrer_telegram_id: Referrer telegram ID
            advanced_user_name: Yuqori darajaga chiqgan foydalanuvchi ismi
            advanced_user_level: Yuqori darajaga chiqgan foydalanuvchi darajasi
            referrer_level: Referrer hozirgi darajasi
        """
        deadline = timezone.now() + timedelta(hours=24)
        deadline_str = deadline.strftime('%d.%m.%Y %H:%M')
        
        message = f"""⚠️ <b>MUHIM XABAR!</b>

🔔 Sizning referalingiz <b>{advanced_user_name}</b> sizdan yuqori darajaga chiqdi:

📊 <b>Darajalar:</b>
• Uning darajasi: <code>{advanced_user_level}</code>
• Sizning darajangiz: <code>{referrer_level}</code>

⏰ <b>Sizga 24 soat vaqt beriladi!</b>
📅 Tugash vaqti: <b>{deadline_str}</b>

❗️ <b>Agar bu vaqt ichida darajangizni oshirmasangiz:</b>
Admin tomonidan sizning o'rningizga boshqa referrer belgilanadi.

💡 <b>Darajangizni oshirish uchun:</b>
• Kurs sotib oling
• Faol bo'ling
• Referrallar olib keling

🚀 Muvaffaqiyatlar tilaymiz!"""

        return await TelegramNotification.send_message(referrer_telegram_id, message)

    @staticmethod
    async def send_referrer_changed_notification(user_telegram_id: str, old_referrer_name: str, 
                                                new_referrer_name: str, admin_name: str):
        """
        Foydalanuvchiga referrer almashtirilganligi haqida xabar
        """
        message = f"""🔄 <b>REFERRER ALMASHTIRILDI</b>

👤 Sizning referreringiz o'zgartirildi:

📤 <b>Eski referrer:</b> {old_referrer_name}
📥 <b>Yangi referrer:</b> {new_referrer_name}

👨‍💼 <b>Admin:</b> {admin_name} tomonidan amalga oshirildi.

ℹ️ Bu o'zgarish sizning hisobingizga ta'sir qilmaydi."""

        return await TelegramNotification.send_message(user_telegram_id, message)

    @staticmethod
    async def send_new_referral_notification(referrer_telegram_id: str, new_referral_name: str, 
                                           new_referral_level: str, admin_name: str):
        """
        Yangi referrerga yangi referral qo'shilganligi haqida xabar
        """
        message = f"""👥 <b>YANGI REFERRAL QO'SHILDI!</b>

🎉 Sizga yangi referral qo'shildi:

👤 <b>Foydalanuvchi:</b> {new_referral_name}
📊 <b>Daraja:</b> <code>{new_referral_level}</code>

👨‍💼 <b>Admin:</b> {admin_name} tomonidan qo'shildi.

🔥 <b>Tabriklaymiz!</b> Referrallar soningingiz oshdi.
💰 Bu sizning daromadingizni oshiradi!"""

        return await TelegramNotification.send_message(referrer_telegram_id, message)

    @staticmethod
    async def send_referral_removed_notification(old_referrer_telegram_id: str, removed_referral_name: str, 
                                               removed_referral_level: str, admin_name: str):
        """
        Eski referrerga referral olib tashlanganligini bildirish
        """
        message = f"""📉 <b>REFERRAL OLIB TASHLANDI</b>

😔 Sizdan bir referral olib tashlandi:

👤 <b>Foydalanuvchi:</b> {removed_referral_name}
📊 <b>Daraja:</b> <code>{removed_referral_level}</code>

👨‍💼 <b>Admin:</b> {admin_name} tomonidan amalga oshirildi.

❗️ <b>Sabab:</b> Foydalanuvchi darajasi sizning darajangizdan yuqori bo'lgani uchun.

💪 <b>Tavsiya:</b>
• Darajangizni oshiring
• Kurslarni sotib oling
• Faol bo'ling!"""

        return await TelegramNotification.send_message(old_referrer_telegram_id, message)

    @staticmethod
    async def send_level_upgrade_success(user_telegram_id: str, old_level: str, new_level: str):
        """
        Foydalanuvchi darajasi oshganligini xabar qilish
        """
        message = f"""🎉 <b>DARAJA OSHIRILDI!</b>

🆙 Tabriklaymiz! Sizning darajangiz oshirildi:

📈 <b>Eski daraja:</b> <code>{old_level}</code>
🆕 <b>Yangi daraja:</b> <code>{new_level}</code>

🔥 <b>Yangi imkoniyatlar:</b>
• Yuqori darajali kurslar
• Ko'proq referral bonuslari
• Maxsus chegirmalar

🚀 Davom eting va yanada yuqori cho'qqilarga chiqing!</b>"""

        return await TelegramNotification.send_message(user_telegram_id, message)

    @staticmethod
    async def send_payment_confirmed(user_telegram_id: str, amount: float, course_name: str = None):
        """
        To'lov tasdiqlangani haqida xabar
        """
        if course_name:
            message = f"""✅ <b>TO'LOV TASDIQLANDI!</b>

💰 <b>To'lov miqdori:</b> {amount:,.0f} so'm
📚 <b>Kurs:</b> {course_name}

🎉 Tabriklaymiz! Siz kursga qabul qilindingiz.
📲 Tez orada yopiq kanalga taklif qilinasiz.

📈 Muvaffaqiyatli o'qishlar!"""
        else:
            message = f"""✅ <b>TO'LOV TASDIQLANDI!</b>

💰 <b>To'lov miqdori:</b> {amount:,.0f} so'm

🎉 Tabriklaymiz! To'lovingiz tasdiqlandi."""

        return await TelegramNotification.send_message(user_telegram_id, message)

    @staticmethod
    async def send_payment_rejected(user_telegram_id: str, amount: float, reason: str):
        """
        To'lov rad etilgani haqida xabar
        """
        message = f"""❌ <b>TO'LOV RAD ETILDI</b>

💰 <b>To'lov miqdori:</b> {amount:,.0f} so'm
❗️ <b>Sabab:</b> {reason}

🔄 <b>Nima qilish kerak:</b>
• To'lov kvitansiyasini qayta tekshiring
• To'g'ri miqdorda to'lov qiling
• Yangidan ariza bering

📞 Savollar bo'lsa admin bilan bog'laning."""

        return await TelegramNotification.send_message(user_telegram_id, message)

    @staticmethod
    async def send_bulk_message(user_ids: list, message: str):
        """
        Bir nechta foydalanuvchiga xabar yuborish
        
        Args:
            user_ids: Foydalanuvchilar telegram ID lari ro'yxati
            message: Yuborilishi kerak bo'lgan xabar
        
        Returns:
            dict: Yuborish natijasi statistikasi
        """
        successful_sends = 0
        failed_sends = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                result = await TelegramNotification.send_message(user_id, message)
                if result["success"]:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    failed_users.append({
                        "user_id": user_id,
                        "error": result["error"]
                    })
                
                # Rate limiting uchun kichik kutish
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_sends += 1
                failed_users.append({
                    "user_id": user_id,
                    "error": str(e)
                })
                logger.error(f"Error sending to {user_id}: {str(e)}")
        
        return {
            "total": len(user_ids),
            "successful": successful_sends,
            "failed": failed_sends,
            "failed_users": failed_users
        }

# Asynchronous wrapper functions for easy use

async def notify_referrer_warning(referrer_telegram_id: str, advanced_user_name: str, 
                                 advanced_user_level: str, referrer_level: str):
    """Referrerga ogohlantirish yuborish"""
    return await TelegramNotification.send_referrer_warning(
        referrer_telegram_id, advanced_user_name, advanced_user_level, referrer_level
    )

async def notify_referrer_changed(user_telegram_id: str, old_referrer_name: str, 
                                 new_referrer_name: str, admin_name: str):
    """Referrer almashtirilgani haqida xabar"""
    return await TelegramNotification.send_referrer_changed_notification(
        user_telegram_id, old_referrer_name, new_referrer_name, admin_name
    )

async def notify_new_referral(referrer_telegram_id: str, new_referral_name: str, 
                             new_referral_level: str, admin_name: str):
    """Yangi referral qo'shilgani haqida xabar"""
    return await TelegramNotification.send_new_referral_notification(
        referrer_telegram_id, new_referral_name, new_referral_level, admin_name
    )

async def notify_referral_removed(old_referrer_telegram_id: str, removed_referral_name: str, 
                                 removed_referral_level: str, admin_name: str):
    """Referral olib tashlanganligini bildirish"""
    return await TelegramNotification.send_referral_removed_notification(
        old_referrer_telegram_id, removed_referral_name, removed_referral_level, admin_name
    )

async def notify_level_upgrade(user_telegram_id: str, old_level: str, new_level: str):
    """Daraja oshganligini xabar qilish"""
    return await TelegramNotification.send_level_upgrade_success(
        user_telegram_id, old_level, new_level
    )

async def notify_payment_confirmed(user_telegram_id: str, amount: float, course_name: str = None):
    """To'lov tasdiqlangani haqida xabar"""
    return await TelegramNotification.send_payment_confirmed(
        user_telegram_id, amount, course_name
    )

async def notify_payment_rejected(user_telegram_id: str, amount: float, reason: str):
    """To'lov rad etilgani haqida xabar"""
    return await TelegramNotification.send_payment_rejected(
        user_telegram_id, amount, reason
    )

async def send_message_to_all_admins(message: str):
    """
    Barcha adminlarga xabar yuborish
    
    Args:
        message: Yuborilishi kerak bo'lgan xabar matni
    
    Returns:
        dict: Yuborish natijasi statistikasi
    """
    try:
        # Django ORM dan foydalanib barcha adminlarni olish
        from bot.models import TelegramUser
        
        # Barcha admin foydalanuvchilarning telegram ID larini olish
        admin_ids = []
        async for admin in TelegramUser.objects.filter(is_admin=True).values_list('telegram_id', flat=True):
            admin_ids.append(str(admin))
        
        if not admin_ids:
            logger.warning("No admins found in database")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "failed_users": [],
                "message": "Adminlar topilmadi"
            }
        
        logger.info(f"Sending message to {len(admin_ids)} admins")
        
        # Barcha adminlarga xabar yuborish
        result = await TelegramNotification.send_bulk_message(admin_ids, message)
        
        logger.info(f"Admin notification result: {result['successful']}/{result['total']} successful")
        return result
        
    except Exception as e:
        logger.error(f"Error sending message to all admins: {str(e)}")
        return {
            "total": 0,
            "successful": 0,
            "failed": 1,
            "failed_users": [],
            "error": str(e)
        }