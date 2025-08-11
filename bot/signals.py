import json
import requests
from django.dispatch import receiver
from django.db.models.signals import post_save
from core.settings import TELEGRAM_BOT_TOKEN
from .models import Payments
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_menu_keyboard_json() -> dict:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Mening hisobim")],
            [
                KeyboardButton(text="📞 Aloqa"),
                KeyboardButton(text="⚡️ Bosqichlar"),
            ],
            [
                KeyboardButton(text="📑 Loyiha haqida"),
                KeyboardButton(text="👥 Mening jamoam"),
            ],
            [
                KeyboardButton(text="❓ Yordam"),
                KeyboardButton(text="🏆 Sovg'alar"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=2,
    )
    # None qiymatlarni chiqarib tashlash
    return keyboard.model_dump(exclude_none=True)

@receiver(post_save, sender=Payments)
def handle_payment_confirmation(sender, instance, created, **kwargs):
    # Loop oldini olish
    if getattr(instance, "_signal_handled", False):
        return

    if instance.status == 'CONFIRMED':
        instance._signal_handled = True

        # confirm_payment() chaqirish
        try:
            instance.confirm_payment()
        except Exception as e:
            print(f"[ERROR] confirm_payment() ishlashida xato: {e}")

        try:
            # Foydalanuvhiga To'langan kursni Private Kanal linkini yuborish
            
            chat_id = instance.user.telegram_id
            message = (
                f"✅ To'lov muvaffaqiyatli amalga oshirildi!\n"
                f"💰 Summa: {instance.amount} so'm\n\n"
                f"🔐 Kurs kanaliga kirish uchun <a href='{instance.course.private_channel}'>👉👉bu yerga bosing👈👈</a>"
            )
            reply_markup = get_menu_keyboard_json()

            # DEBUG LOG — yuboriladigan malumotlarni ko'rsatish
            print("==== TELEGRAM DEBUG ====")
            print(f"Chat ID: {chat_id} ({type(chat_id)})")
            print(f"Message: {message}")
            print("Reply Markup (dict):")
            print(json.dumps(reply_markup, ensure_ascii=False, indent=2))
            print("========================")

            payload = {
                'chat_id': chat_id,
                'text': message,
                'reply_markup': reply_markup
            }

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(url, json=payload)

            # Telegram javobini ham ko'ramiz
            print("==== TELEGRAM RESPONSE ====")
            print(f"Status Code: {response.status_code}")
            try:
                print(response.json())
            except Exception:
                print(response.text)
            print("===========================")

            response.raise_for_status()

        except Exception as e:
            print(f"Telegramga yuborishda xatolik: {e}")

    elif instance.status == 'REJECTED':
        instance._signal_handled = True

        try:
            chat_id = instance.user.telegram_id
            message = "❌ To'lov rad etildi. Iltimos, qayta urinib ko'ring."
            reply_markup = get_menu_keyboard_json()

            # DEBUG LOG — yuboriladigan malumotlarni ko‘rsatish
            print("==== TELEGRAM DEBUG ====")
            print(f"Chat ID: {chat_id} ({type(chat_id)})")
            print(f"Message: {message}")
            print("Reply Markup (dict):")
            print(json.dumps(reply_markup, ensure_ascii=False, indent=2))
            print("========================")

            payload = {
                'chat_id': chat_id,
                'text': message,
                'reply_markup': reply_markup
            }

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(url, json=payload)

            # Telegram javobini ham ko‘ramiz
            print("==== TELEGRAM RESPONSE ====")
            print(f"Status Code: {response.status_code}")
            try:
                print(response.json())
            except Exception:
                print(response.text)
            print("===========================")

            response.raise_for_status()

        except Exception as e:
            print(f"Telegramga yuborishda xatolik: {e}")