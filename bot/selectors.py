from asgiref.sync import sync_to_async
from django.db.models import Q
from .models import (
    TelegramUser,
    MandatoryChannel,
    Konkurslar,
    Payments,
    Kurslar
   
)
from datetime import datetime

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

@sync_to_async
def get_konkurs_participants(konkurs_id):
    konkurs = Konkurslar.objects.filter(id=konkurs_id).first()
    if konkurs:
        return list(konkurs.participants.filter(
            payments__status='CONFIRMED'
        ).distinct())
    return []




@sync_to_async
def get_active_konkurslar():
    now = datetime.now()
    return list(Konkurslar.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at'))

@sync_to_async
def get_konkurs_details(konkurs_id):
    return Konkurslar.objects.filter(id=konkurs_id).first()


@sync_to_async
def get_konkurs_participants_count(konkurs_id):
    konkurs = Konkurslar.objects.get(id=konkurs_id)
    return konkurs.payments.filter(status='CONFIRMED').values('user').distinct().count()

@sync_to_async
def is_konkurs_full(konkurs_id):
    konkurs = Konkurslar.objects.get(id=konkurs_id)
    if konkurs.max_participants:
        return get_konkurs_participants_count.__wrapped__(konkurs_id) >= konkurs.max_participants
    return False

@sync_to_async
def get_user_active_payments(user_id):
    """Foydalanuvchining faol (tasdiqlangan va muddati tugamagan) to'lovlarini olish"""
    return list(Payments.objects.filter(
        Q(user__telegram_id=user_id),
        Q(status='CONFIRMED'),
        Q(konkurs__isnull=False) & Q(konkurs__end_date__gte=datetime.now()) | 
        Q(course__isnull=False) & Q(course__is_active=True)
    ))

@sync_to_async
def get_active_konkurslar():
    """Faol konkurslarni olish"""
    now = datetime.now()
    return list(Konkurslar.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('-created_at'))

@sync_to_async
def get_active_kurslar():
    """Faol kurslarni olish"""
    return list(Kurslar.objects.filter(
        is_active=True
    ).order_by('-created_at'))

@sync_to_async
def get_konkurs_details(konkurs_id):
    """Konkurs tafsilotlarini olish"""
    return Konkurslar.objects.filter(id=konkurs_id).first()

@sync_to_async
def get_kurs_details(kurs_id):
    """Kurs tafsilotlarini olish"""
    return Kurslar.objects.filter(id=kurs_id).first()

@sync_to_async
def create_payment_request(user_id, payment_type, amount, konkurs_id=None, kurs_id=None, photo_path=None):
    """Yangi to'lov so'rovini yaratish"""
    user = TelegramUser.objects.filter(telegram_id=user_id).first()
    if not user:
        return None
    
    payment = Payments(
        user=user,
        payment_type=payment_type,
        amount=amount,
        status='PENDING'
    )
    
    if payment_type == 'KONKURS' and konkurs_id:
        payment.konkurs = Konkurslar.objects.filter(id=konkurs_id).first()
    elif payment_type == 'COURSE' and kurs_id:
        payment.course = Kurslar.objects.filter(id=kurs_id).first()
    
    if photo_path:
        payment.payment_screenshot = photo_path
    
    payment.save()
    return payment

@sync_to_async
def get_konkurs_participants_count(konkurs_id):
    """Konkurs ishtirokchilari sonini olish"""
    return Payments.objects.filter(
        konkurs_id=konkurs_id,
        status='CONFIRMED'
    ).values('user').distinct().count()

@sync_to_async
def get_kurs_participants_count(kurs_id):
    """Kurs ishtirokchilari sonini olish"""
    return Payments.objects.filter(
        course_id=kurs_id,
        status='CONFIRMED'
    ).values('user').distinct().count()


@sync_to_async
def confirm_payment(payment_id, admin_user_id):
    """To'lovni tasdiqlash"""
    payment = Payments.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()
    
    if payment and admin_user:
        payment.status = 'CONFIRMED'
        payment.confirmed_by = admin_user
        payment.confirmed_date = datetime.now()
        payment.save()
        return True
    return False

@sync_to_async
def reject_payment(payment_id, admin_user_id, reason):
    """To'lovni rad etish"""
    payment = Payments.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()
    
    if payment and admin_user:
        payment.status = 'REJECTED'
        payment.confirmed_by = admin_user
        payment.confirmed_date = datetime.now()
        payment.rejection_reason = reason
        payment.save()
        return True
    return False

@sync_to_async
def get_user_buy_course(telegram_id):
    """
    Foydalanuvchi birorta kurs sotib olganmi yoki yo'qligini tekshiradi.
    True yoki False qaytaradi.
    """
    return Payments.objects.filter(
        user__telegram_id=telegram_id,
        course__isnull=False,
        status='CONFIRMED'
    ).exists()

@sync_to_async
def get_all_active_courses():
    """
    Barcha faol kurslarni olish.
    """
    return list(Kurslar.objects.filter(is_active=True).order_by('-created_at'))