from asgiref.sync import sync_to_async
from django.db.models import Q
from .models import (
    TelegramUser,
    MandatoryChannel,
    Payments,
    Kurslar
   
)
from datetime import datetime
# Level mapping dictionary
LEVEL_MAPPING = {
    "1-bosqich": "level_1",
    "2-bosqich": "level_2", 
    "3-bosqich": "level_3",
    "4-bosqich": "level_4",
    "5-bosqich": "level_5",
    # Agar boshqa levellar ham bo'lsa qo'shishingiz mumkin
}

# Teskari mapping
REVERSE_LEVEL_MAPPING = {v: k for k, v in LEVEL_MAPPING.items()}

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
def get_user_level(telegram_id):
    """
    Foydalanuvchini levelini olish
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if user:
            print(f"User found: {user.full_name}, Level: {user.level}")
            return user.level
        else:
            print(f"User not found for telegram_id: {telegram_id}")
            return None
    except Exception as e:
        print(f"Error getting user level: {e}")
        return None

@sync_to_async
def get_level_kurs(level: str):
    """
    Ma'lum level bo'yicha faol kursni olish - Mapping bilan
    """
    try:
        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(level, level)
        print(f"Looking for course with user level: {level}, mapped to course level: {course_level}")
        
        course = Kurslar.objects.filter(is_active=True, level=course_level).order_by('-created_at').first()
        
        if course:
            print(f"Found course: {course.name}, Level: {course.level}")
        else:
            print(f"No course found for level: {course_level}")
            # Barcha faol kurslarni ko'rsatish
            all_courses = list(Kurslar.objects.filter(is_active=True).values('name', 'level'))
            print(f"Available courses: {all_courses}")
            
            # Agar aniq level topilmasa, birinchi faol kursni qaytarish
            course = Kurslar.objects.filter(is_active=True).order_by('-created_at').first()
            if course:
                print(f"Using first available course: {course.name}")
                
        return course
    except Exception as e:
        print(f"Error getting course: {e}")
        return None

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
def get_user_active_payments(user_id):
    """Foydalanuvchining faol (tasdiqlangan va muddati tugamagan) to'lovlarini olish"""
    return list(Payments.objects.filter(
        Q(user__telegram_id=user_id),
        Q(status='CONFIRMED'),
        Q(course__isnull=False) & Q(course__is_active=True)
    ))

@sync_to_async
def get_active_kurslar():
    """Faol kurslarni olish"""
    return list(Kurslar.objects.filter(
        is_active=True
    ).order_by('-created_at'))

@sync_to_async
def get_kurs_details(kurs_id):
    """Kurs tafsilotlarini olish"""
    return Kurslar.objects.filter(id=kurs_id).first()

@sync_to_async
def create_payment_request(user_id, payment_type, amount, kurs_id=None, photo_path=None):
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

    if payment_type == 'COURSE' and kurs_id:
        payment.course = Kurslar.objects.filter(id=kurs_id).first()
    
    if photo_path:
        payment.payment_screenshot = photo_path
    
    payment.save()
    return payment

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
    Barcha faol kurslarni olish (QuerySet).
    """
    return Kurslar.objects.filter(is_active=True).order_by('-created_at')

@sync_to_async
def get_first_active_course():
    """Birinchi faol kursni olish"""
    return Kurslar.objects.filter(is_active=True).order_by('-created_at').first()

@sync_to_async
def get_all_active_courses_list():
    """
    Barcha faol kurslarni olish - list qaytaradi, QuerySet emas
    """
    return list(Kurslar.objects.filter(is_active=True).order_by('-created_at'))


@sync_to_async
def get_course_by_user_level(user_level: str):
    """
    Foydalanuvchi leveliga mos birinchi faol kursni olish
    """
    try:
        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(user_level, user_level)
        print(f"Looking for course with user level: {user_level}, mapped to course level: {course_level}")
        
        # Faqat shu levelga mos faol kursni olish
        course = Kurslar.objects.filter(
            is_active=True, 
            level=course_level
        ).order_by('-created_at').first()
        
        if course:
            print(f"Found course for level {course_level}: {course.name}")
        else:
            print(f"No course found for level: {course_level}")
            
        return course
    except Exception as e:
        print(f"Error getting course by user level: {e}")
        return None