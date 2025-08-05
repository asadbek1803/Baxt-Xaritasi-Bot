from asgiref.sync import sync_to_async
from .models import (
    TelegramUser,
    MandatoryChannel
   
)


@sync_to_async
def fetch_user(chat_id: str):
    return TelegramUser.objects.filter(telegram_id=chat_id).first()


async def get_user(chat_id: str) -> bool | TelegramUser:
    user = await fetch_user(chat_id)
    return user or False

@sync_to_async
def create_user(user_data: dict):
    """Yangi foydalanuvchi yaratish"""
    return TelegramUser.objects.create(**user_data)


@sync_to_async
def get_referrer_by_id(telegram_id: str):
    """Referrer ni topish"""
    return TelegramUser.objects.filter(telegram_id=telegram_id).first()

@sync_to_async
def get_all_admins():
    """Barcha adminlarni olish"""
    return list(TelegramUser.objects.filter(is_admin=True).values_list('telegram_id', flat=True))

@sync_to_async
def get_all_channels():
    """Barcha majburiy kanallarni olish"""
    return list(MandatoryChannel.objects.filter(is_active=True))