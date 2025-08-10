import os
import requests
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.core.cache import cache
from .models import Payments, Notification 
from bot.buttons.default.menu import get_menu_keyboard

@receiver(post_save, sender=Payments)
def handle_payment_confirmation(sender, instance, created, **kwargs):
    # Faqat yangi yoki yangilangan va hali tasdiqlanmagan to'lovlar uchun
    if instance.status == 'CONFIRMED' and not instance.is_confirmed:
        instance.confirm_payment()

        telegram_token = os.getenv("BOT_TOKEN", "Defualt token")
        chat_id = instance.user.telegram_id
        message = f"✅ To'lov muvaffaqiyatli amalga oshirildi!\n{instance.amount} so'm"
        reply_markup = get_menu_keyboard()
        payload = {
            'chat_id': chat_id,
            'text': message,
            'reply_markup': reply_markup
        }

        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Telegramga yuborishda xatolik: {e}")

