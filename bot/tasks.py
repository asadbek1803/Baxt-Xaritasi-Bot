from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .models import TelegramUser
from bot.views import bot
import asyncio


@shared_task(bind=True)
def update_loosers_referalls_to_admin(self):
    """Loserlarning referallarini admin userlarga o'tkazish"""
    try:
        loosers = TelegramUser.objects.filter(
            is_looser=True, inactive_time__date=timezone.now().date()
        ).select_related("invited_by")

        admin_user = TelegramUser.objects.filter(is_admin=True).first()

        if not admin_user:
            print("[ERROR] No admin user found")
            return

        for looser in loosers:
            if looser.inactive_time < timezone.now():
                # Get all invitees of this loser
                invitees = TelegramUser.objects.filter(invited_by=looser)

                for invitee in invitees:
                    invitee.invited_by = admin_user
                    invitee.save()

                # Reset loser status
                looser.is_looser = False
                looser.inactive_time = None
                looser.save()

                print(
                    f"[SUCCESS] Transferred {invitees.count()} invitees from loser {looser.telegram_id} to admin"
                )

    except Exception as e:
        print(f"[ERROR] Error in update_loosers_referalls_to_admin: {e}")


@shared_task(bind=True)
def check_active_users(self):
    """Aktiv foydalanuvchilarni tekshirish va aktivlik tasdiqlash so'rovini yuborish"""
    try:
        # Get users who haven't confirmed activity in the last 48 hours
        deadline_for_activation = timezone.now() + timedelta(hours=48)

        users_to_check = TelegramUser.objects.filter(
            is_active=True,
        )

        print(
            f"[INFO] Checking {users_to_check.count()} users for activity confirmation"
        )

        for user in users_to_check:
            try:
                # Create inline keyboard with "Men aktivman" button
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Men aktivman",
                                callback_data=f"confirm_activity_{user.telegram_id}",
                            )
                        ]
                    ]
                )

                # Send message with inline button
                message_text = (
                    "🔔 <b>Aktivlik tekshiruvi</b>\n\n"
                    "Siz botimizdan aktiv tarzda foydalanmoqdamisiz? "
                    "Iltimos, aktivligingizni quyidagi tugma orqali tasdiqlang.\n\n"
                    "⏰ Sizda <b>48 soat</b> vaqt bor, aks holda loyihamizdan chetlashtirilasiz!"
                )

                async def send_activity_check():
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )

                asyncio.run(send_activity_check())

                # Update last activity check time
                user.deadline_for_activation = deadline_for_activation
                user.save()

                print(f"[SUCCESS] Activity check sent to user {user.telegram_id}")

            except Exception as e:
                print(
                    f"[ERROR] Failed to send activity check to user {user.telegram_id}: {e}"
                )
                continue

    except Exception as e:
        print(f"[ERROR] Error in check_active_users: {e}")


@shared_task(bind=True)
def deactivate_inactive_users(self):
    """48 soat ichida aktivlik tasdiqlanmagan foydalanuvchilarni deaktiv qilish"""
    try:
        deadline_for_activation = timezone.now()

        inactive_users = TelegramUser.objects.filter(
            deadline_for_activation__date=deadline_for_activation.date(),
        )

        print(f"[INFO] Deactivating {inactive_users.count()} inactive users")
        admin_user = TelegramUser.objects.filter(is_admin=True).first()
        for user in inactive_users:
            try:
                user.is_active = False
                user.is_looser = True
                user.deadline_for_activation = None
                user.save()

                invitees = TelegramUser.objects.filter(invited_by=user)

                for invitee in invitees:
                    invitee.invited_by = admin_user
                    invitee.save()

                # Notify user about deactivation
                asyncio.run(
                    bot.send_message(
                        chat_id=user.telegram_id,
                        text="❌ Siz 48 soat ichida aktivlik tasdiqlanmaganingiz uchun loyihamizdan chetlashtirildingiz.",
                    )
                )

                print(f"[SUCCESS] User {user.telegram_id} deactivated")

            except Exception as e:
                print(f"[ERROR] Failed to deactivate user {user.telegram_id}: {e}")
                continue

    except Exception as e:
        print(f"[ERROR] Error in deactivate_inactive_users: {e}")
