import requests

from django.dispatch import receiver
from django.db.models.signals import post_save
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from core.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME
from .models import Payments, ReferralPayment

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


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
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=2,
    )
    # None qiymatlarni chiqarib tashlash
    return keyboard.model_dump(exclude_none=True)


@receiver(post_save, sender=Payments)
def handle_payment_confirmation(sender, instance, created, **kwargs):
    if getattr(instance, "_signal_handled", False):
        return

    if instance.status == "CONFIRMED":
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
                f"🔐 Kurs kanaliga kirish uchun quyidagi tugmani bosing:"
            )
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📲 Kurs kanaliga kirish",
                            url=instance.course.private_channel,
                        )
                    ]
                ]
            ).model_dump(exclude_none=True)
            payload = {
                "chat_id": chat_id,
                "text": message,
                "reply_markup": reply_markup,
                "parse_mode": "HTML",
            }
            response = requests.post(BASE_URL, json=payload)
            response.raise_for_status()

            message = f"""
Keyingi qadam endi siz sizni bu loyihaga qo'shilishingizga sababchi bo'lgan liderga daromadini tashlab berishingiz kerak.
Belgilangan summa 200 000 so’m.
To'lov qilishingiz uchun hamkorning telegram lichkasiga yozib yoki ushbu telefon raqamga telefon qilib karta raqam oling va to'lov qiling.
Va shundan so'ng, siz ham o'z shaxsiy referalingizga ega bo'lasiz va yaqinlaringizni taklif qila olasiz.
hamkor ismi : {instance.user.invited_by.full_name}, \nKarta raqami: {instance.user.invited_by.card_number}
"""
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📢 Referral yaratish",
                            callback_data=f"create_referral_{instance.course.id}"
                        )
                    ]
                ]
            ).model_dump(exclude_none=True)

            payload = {
                "chat_id": chat_id,
                "text": message,
                "reply_markup": reply_markup,
                "parse_mode": "HTML",
            }
            response = requests.post(BASE_URL, json=payload)
            response.raise_for_status()

        except Exception as e:
            print(f"Telegramga yuborishda xatolik: {e}")

    elif instance.status == "REJECTED":
        instance._signal_handled = True

        try:
            chat_id = instance.user.telegram_id
            message = "❌ To'lov rad etildi. Iltimos, qayta urinib ko'ring."
            reply_markup = get_menu_keyboard_json()

            payload = {
                "chat_id": chat_id,
                "text": message,
                "reply_markup": reply_markup,
                "parse_mode": "HTML",
            }

            response = requests.post(BASE_URL, json=payload)
            response.raise_for_status()

        except Exception as e:
            print(f"Telegramga yuborishda xatolik: {e}")


@receiver(post_save, sender=ReferralPayment)
def handle_referral_payment_confirmation(sender, instance, created, **kwargs):

    if getattr(instance, "_signal_handled", False):
        return

    if instance.status == "CONFIRMED":
        user = instance.user
        instance._signal_handled = True
        referral_link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={user.referral_code}"
        message = "Siznig to'lovingiz admin tomonidan tasdiqlandi \n\n"
        message += "🎯 Sizning Referral Ma'lumotlaringiz:\n\n"
        message += f"🆔 Referral ID: {user.telegram_id}\n"
        message += f"🔑 Referral kod: {user.referral_code}\n"
        message += f"👥 To'liq ismingiz: {user.full_name}\n"
        message += f"💰 To'langan summa: {instance.amount:,} so'm\n"
        message += f"📅 To'lov vaqti: {instance.created_at.strftime('%d-%m-%Y %H:%M')}\n"
        message += "✅ Status: Tasdiqlandi\n\n"
        message += "🔗 Sizning referral havolangiz:\n"
        message += f"{referral_link}"

        payload = {
            "chat_id": user.telegram_id,
            "text": message,
            "reply_markup": get_menu_keyboard_json(),
            "parse_mode": "HTML",
        }
        response = requests.post(BASE_URL, json=payload)
        response.raise_for_status()
