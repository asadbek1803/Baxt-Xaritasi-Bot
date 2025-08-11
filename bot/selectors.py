from asgiref.sync import sync_to_async
from django.db.models import Q, Count
from core.settings import TELEGRAM_BOT_USERNAME
from .models import (
    TelegramUser,
    MandatoryChannel,
    Payments,
    Kurslar,
    ReferralPayment,
    Gifts
)
from datetime import datetime
import uuid

# Level mapping dictionary
LEVEL_MAPPING = {
    "0-bosqich": "level_0",
    "1-bosqich": "level_1",
    "2-bosqich": "level_2", 
    "3-bosqich": "level_3",
    "4-bosqich": "level_4",
    "5-bosqich": "level_5",
    "6-bosqich": "level_6",
    "7-bosqich": "level_7",
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
    ).select_related('course'))

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
        # User level formatini tekshirish va to'g'rilash
        if user_level.startswith('level_'):
            # Agar level_1 formatida bo'lsa, uni 1-bosqich formatiga o'tkazish
            level_num = user_level.split('_')[1]
            user_level = f"{level_num}-bosqich"
        
        # User level-ini int ga o'tkazamiz
        user_level_int = int(user_level.split('-')[0])
        
        # Agar user level 7 dan katta bo'lsa, birinchi faol kursni qaytaramiz
        if user_level_int > 6:
            print(f"User level {user_level} dan yuqori, birinchi faol kurs qaytariladi.")
            return Kurslar.objects.filter(is_active=True).order_by('-created_at').first()

        # Keyingi bosqich nomini aniqlaymiz
        next_level_int = user_level_int + 1
        next_level = f"{next_level_int}-bosqich"

        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(next_level, next_level)
        print(f"Looking for course for user level: {user_level}, mapped to course level: {course_level}")
        
        # Faqat shu levelga mos faol kursni olish
        course = Kurslar.objects.filter(
            is_active=True, 
            level=course_level
        ).order_by('-created_at').first()
        
        if course:
            print(f"Found course for level {course_level}: {course.name}")
        else:
            print(f"No course found for level: {course_level}, returning first active course")
            course = Kurslar.objects.filter(is_active=True).order_by('-created_at').first()
            
        return course
    except Exception as e:
        print(f"Error getting course by user level: {e}")
        return Kurslar.objects.filter(is_active=True).order_by('-created_at').first()

@sync_to_async
def get_user_level(telegram_id):
    """
    Foydalanuvchini levelini olish va formatini to'g'rilash
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if user and user.level:
            # Level formatini tekshirish va to'g'rilash
            if user.level.startswith('level_'):
                # level_1 -> 1-bosqich
                level_num = user.level.split('_')[1]
                corrected_level = f"{level_num}-bosqich"
                print(f"User found: {user.full_name}, Level: {user.level} -> corrected to: {corrected_level}")
                return corrected_level
            else:
                print(f"User found: {user.full_name}, Level: {user.level}")
                return user.level
        else:
            print(f"User not found or no level for telegram_id: {telegram_id}")
            return "0-bosqich"  # Default level
    except Exception as e:
        print(f"Error getting user level: {e}")
        return "0-bosqich"

@sync_to_async
def get_level_kurs(level: str):
    """
    Ma'lum level bo'yicha faol kursni olish - Mapping bilan
    """
    try:
        # Level formatini tekshirish va to'g'rilash
        if level.startswith('level_'):
            level_num = level.split('_')[1]
            level = f"{level_num}-bosqich"
        
        # User level-ini int ga o'tkazamiz
        user_level_int = int(level.split('-')[0])

        # Keyingi bosqich nomini aniqlaymiz
        next_level_int = user_level_int + 1
        next_level = f"{next_level_int}-bosqich"

        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(next_level, next_level)
        print(f"Looking for course with user level: {level}, mapped to course level: {course_level}")
        
        course = Kurslar.objects.filter(is_active=True, level=course_level).order_by('-created_at').first()
        
        if course:
            print(f"Found course: {course.name}, Level: {course.level}")
        
        return course
    except Exception as e:
        print(f"Error getting course: {e}")
        return None

@sync_to_async
def check_user_referral_code(referral_code: str):
    """
    Referal kodni tekshirish
    """
    try:
        user = TelegramUser.objects.filter(referral_code=referral_code).first()
        if user:
            print(f"Referal code {referral_code} is valid for user: {user.full_name}")
            return user
        else:
            print(f"Referal code {referral_code} is not valid.")
            return None
    except Exception as e:
        print(f"Error checking referal code: {e}")
        return None

@sync_to_async
def get_user_purchased_courses_with_levels(telegram_id: str):
    """
    Foydalanuvchi sotib olgan kurslar levellarini set ko'rinishida qaytaradi
    Django ORM relationship muammosini hal qilish uchun
    """
    try:
        # select_related bilan course ma'lumotlarini olish
        payments = Payments.objects.filter(
            user__telegram_id=telegram_id,
            course__isnull=False,
            status='CONFIRMED'
        ).select_related('course')
        
        purchased_course_levels = set()
        for payment in payments:
            if payment.course and payment.course.level:
                print(f"Found purchased course: {payment.course.name}, Level: {payment.course.level}")
                
                # Course level ni user level formatiga o'girish
                course_level = REVERSE_LEVEL_MAPPING.get(payment.course.level, payment.course.level)
                if course_level:
                    try:
                        # Course level formatini tekshirish
                        if course_level.startswith('level_'):
                            level_num = course_level.split('_')[1]
                            course_level = f"{level_num}-bosqich"
                        
                        purchased_level_num = int(course_level.split('-')[0])
                        purchased_course_levels.add(purchased_level_num)
                        print(f"Added level {purchased_level_num} to purchased levels")
                    except (ValueError, AttributeError) as e:
                        print(f"Error processing course level {payment.course.level}: {e}")
                        continue
        
        print(f"Final purchased course levels: {purchased_course_levels}")
        return purchased_course_levels
    except Exception as e:
        print(f"Error getting user purchased courses with levels: {e}")
        return set()

@sync_to_async
def update_user_level(telegram_id: str, new_level: str):
    """
    Foydalanuvchi levelini yangilash
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if user:
            user.level = new_level
            user.save()
            print(f"User {user.full_name} level updated to: {new_level}")
            return True
        return False
    except Exception as e:
        print(f"Error updating user level: {e}")
        return False

@sync_to_async
def check_user_can_access_level(telegram_id: str, target_level: str):
    """
    Foydalanuvchi ma'lum levelga kirish huquqi borligini tekshirish
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return False
        
        # User level formatini to'g'rilash
        user_level = user.level
        if user_level.startswith('level_'):
            level_num = user_level.split('_')[1]
            user_level = f"{level_num}-bosqich"
        
        # Foydalanuvchining hozirgi level raqamini olish
        try:
            current_level_num = int(user_level.split('-')[0])
            target_level_num = int(target_level.split('-')[0])
        except (ValueError, AttributeError):
            return False
        
        # Agar target level current level dan 1 ta yuqori bo'lsa, oldingi level kursini tekshirish
        if target_level_num == current_level_num + 1:
            previous_level = f"{target_level_num-1}-bosqich"
            course_level = LEVEL_MAPPING.get(previous_level, previous_level)
            
            # Oldingi level kursini sotib olganligini tekshirish
            has_course = Payments.objects.filter(
                user=user,
                course__level=course_level,
                course__is_active=True,
                status='CONFIRMED'
            ).exists()
            
            return has_course
        
        # Agar target level current level dan kichik yoki teng bo'lsa - ruxsat bor
        elif target_level_num <= current_level_num:
            return True
        
        # Boshqa hollarda ruxsat yo'q
        return False
        
    except Exception as e:
        print(f"Error checking user access level: {e}")
        return False

@sync_to_async
def get_user_referrals(user_id: str, limit: int = 8, offset: int = 0):
    """Foydalanuvchining referallarini olish (pagination bilan)"""
    return list(
        TelegramUser.objects.filter(
            invited_by__telegram_id=user_id
        ).order_by('-registration_date')[offset:offset + limit]
    )

@sync_to_async
def get_user_referrals_count(user_id: str) -> int:
    """Foydalanuvchining referallari sonini olish"""
    return TelegramUser.objects.filter(
        invited_by__telegram_id=user_id
    ).count()

@sync_to_async
def get_confirmed_referrals_count(user_id: str) -> int:
    """Foydalanuvchining tasdiqlangan referallari sonini olish"""
    return TelegramUser.objects.filter(
        invited_by__telegram_id=user_id,
        is_confirmed=True
    ).count()

@sync_to_async
def get_monthly_referrals_count(user_id: str) -> int:
    """Bu oy qo'shilgan referallar sonini olish"""
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return TelegramUser.objects.filter(
        invited_by__telegram_id=user_id,
        registration_date__gte=start_of_month
    ).count()

@sync_to_async
def get_referrals_by_level(user_id: str) -> dict:
    """Referallarni daraja bo'yicha guruplash"""
    referrals = TelegramUser.objects.filter(
        invited_by__telegram_id=user_id
    ).values('level').annotate(count=Count('level')).order_by('level')
    
    result = {}
    for item in referrals:
        level = item['level'] or '0-bosqich'
        result[level] = item['count']
    
    return result

@sync_to_async
def get_user_referral_tree(user_id: str, depth: int = 3):
    """Referallar daraxtini olish (chuqurlik bilan)"""
    def build_tree(parent_id: str, current_depth: int = 0):
        if current_depth >= depth:
            return []
        
        children = TelegramUser.objects.filter(
            invited_by__telegram_id=parent_id
        ).order_by('-registration_date')
        
        result = []
        for child in children:
            child_data = {
                'user': child,
                'children': build_tree(child.telegram_id, current_depth + 1)
            }
            result.append(child_data)
        
        return result
    
    return build_tree(user_id)

@sync_to_async
def get_user_referral_levels_stats(user_id: str) -> dict:
    """Foydalanuvchining referallari bo'yicha batafsil statistika"""
    # 1-daraja referallar (to'g'ridan-to'g'ri)
    level_1 = TelegramUser.objects.filter(invited_by__telegram_id=user_id)
    
    # 2-daraja referallar 
    level_2 = TelegramUser.objects.filter(
        invited_by__invited_by__telegram_id=user_id
    )
    
    # 3-daraja referallar
    level_3 = TelegramUser.objects.filter(
        invited_by__invited_by__invited_by__telegram_id=user_id
    )
    
    return {
        'level_1': level_1.count(),
        'level_2': level_2.count(), 
        'level_3': level_3.count(),
        'total': level_1.count() + level_2.count() + level_3.count()
    }

@sync_to_async
def get_top_referrers(limit: int = 10):
    """Eng ko'p referalga ega foydalanuvchilar"""
    return list(
        TelegramUser.objects.annotate(
            referral_count_db=Count('referrals')
        ).filter(
            referral_count_db__gt=0
        ).order_by('-referral_count_db')[:limit]
    )

@sync_to_async
def search_referrals(user_id: str, search_query: str, limit: int = 10):
    """Referallar orasida qidirish"""
    return list(
        TelegramUser.objects.filter(
            invited_by__telegram_id=user_id
        ).filter(
            Q(full_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(telegram_username__icontains=search_query)
        ).order_by('-registration_date')[:limit]
    )

@sync_to_async
def create_referral_payment_request(user_id: str, referrer_id: str, amount: float):
    """Referral to'lov so'rovini yaratish"""
    user = TelegramUser.objects.filter(telegram_id=user_id).first()
    referrer = TelegramUser.objects.filter(telegram_id=referrer_id).first()
    
    if not user or not referrer:
        return None
    
    payment = ReferralPayment(
        user=user,
        referrer=referrer,
        amount=amount,
        payment_type='REFERRAL_BONUS',
        status='PENDING'
    )
    payment.save()
    return payment

@sync_to_async
def get_pending_referral_payments(referrer_id: str):
    """Tasdiqlanishi kerak bo'lgan referral to'lovlarni olish"""
    return list(ReferralPayment.objects.filter(
        referrer__telegram_id=referrer_id,
        payment_type='REFERRAL_BONUS',
        status='PENDING'
    ))

@sync_to_async
def confirm_referral_payment(payment_id: str, admin_user_id: str):
    """Referral to'lovni tasdiqlash"""
    payment = ReferralPayment.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()
    
    if payment and admin_user:
        payment.status = 'CONFIRMED'
        payment.confirmed_by = admin_user
        payment.confirmed_date = datetime.now()
        payment.save()
        
        # Referral kod yaratish
        if not payment.user.referral_code:
            payment.user.referral_code = str(uuid.uuid4())[:8]
            payment.user.save()
        
        return True
    return False

@sync_to_async
def reject_referral_payment(payment_id: str, admin_user_id: str):
    """Referral to'lovni rad etish"""
    payment = ReferralPayment.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()
    
    if payment and admin_user:
        payment.status = 'REJECTED'
        payment.confirmed_by = admin_user
        payment.confirmed_date = datetime.now()
        payment.save()
        return True
    return False

# NEW ASYNC FUNCTION FOR REFERRAL LINK
@sync_to_async
def get_user_referral_link_async(user_info):
    """User referral linkini async tarzda olish - DATABASE ACCESS INCLUDED"""
    try:
        # Agar user modelida get_referral_link methodi mavjud bo'lsa
        if hasattr(user_info, 'get_referral_link'):
            return user_info.get_referral_link()
        else:
            # Agar method yo'q bo'lsa, manual link yaratish
              # Botingizning username ini yozing
            return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={user_info.telegram_id}"
    except Exception as e:
        print(f"Error in get_user_referral_link_async: {e}")
          # Botingizning username ini yozing
        return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={user_info.telegram_id}"

@sync_to_async
def update_user_card_info(telegram_id, card_number, card_holder_name):
    """Foydalanuvchi plastik karta ma'lumotlarini yangilash"""
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        user.card_number = card_number
        user.card_holder_full_name = card_holder_name
        user.save(update_fields=['card_number', 'card_holder_full_name'])
        return True
    except TelegramUser.DoesNotExist:
        return False
    except Exception as e:
        print(f"Error updating card info: {e}")
        return False

# Qo'shimcha async funksiyalar selectors.py-ga qo'shish kerak:

# User field access-larni async qilish uchun qo'shimcha funksiyalar
@sync_to_async
def get_user_phone(user):
    """User phone number-ni async olish"""
    return user.phone_number if user.phone_number else "Mavjud emas"

@sync_to_async  
def get_user_username(user):
    """User telegram username-ni async olish"""
    return f"@{user.telegram_username}" if user.telegram_username else "mavjud emas"

@sync_to_async
def get_user_gender_display(user):
    """User gender-ni display formatda async olish"""
    if user.gender == "M":
        return "Erkak"
    elif user.gender == "F":
        return "Ayol"
    else:
        return "Belgilanmagan"

@sync_to_async
def get_user_age(user):
    """User age-ni async olish"""
    return user.age

@sync_to_async
def get_user_region(user):
    """User region-ni async olish"""
    return user.region

@sync_to_async
def get_user_profession(user):
    """User profession-ni async olish"""
    return user.profession

@sync_to_async
def get_user_registration_date_formatted(user):
    """User registration date-ni formatted holatda async olish"""
    if user.registration_date:
        return user.registration_date.strftime('%d.%m.%Y %H:%M')
    return "Noma'lum"

@sync_to_async
def get_user_level_safe(user):
    """User level-ni async olish"""
    return user.level

@sync_to_async
def get_user_referral_count_safe(user):
    """User referral count-ni async olish"""
    return getattr(user, 'referral_count', 0)

@sync_to_async
def get_user_confirmation_status(user):
    """User confirmation status-ni async olish"""
    return user.is_confirmed

# MAIN FUNCTION - Optimized single function to get all user profile data at once
@sync_to_async
def get_user_profile_data(user):
    try:
        # Foydalanuvchi ma'lumotlarini faqat kerakli maydonlar bilan yuklaymiz
        user = TelegramUser.objects.only(
            "full_name",
            "telegram_id",
            "phone_number",
            "telegram_username",
            "gender",
            "age",
            "region",
            "profession",
            "registration_date",
            "level",
            "is_confirmed"
        ).get(pk=user.pk)

        return {
            'full_name': user.full_name,
            'telegram_id': user.telegram_id,
            'phone': user.phone_number or "Mavjud emas",
            'username': f"@{user.telegram_username}" if user.telegram_username else "mavjud emas",
            'gender': "Erkak" if user.gender == "M" else "Ayol" if user.gender == "F" else "Belgilanmagan",
            'age': user.age,
            'region': user.region,
            'profession': user.profession,
            'registration_date': user.registration_date.strftime('%d.%m.%Y %H:%M') if user.registration_date else "Noma'lum",
            'level': user.level,
            'referral_count': getattr(user, 'referral_count', 0),
            'is_confirmed': user.is_confirmed
        }
    except Exception as e:
        print(f"Error in get_user_profile_data: {e}")
        return {
            'full_name': getattr(user, 'full_name', 'Noma\'lum'),
            'telegram_id': getattr(user, 'telegram_id', ''),
            'phone': "Mavjud emas",
            'username': "mavjud emas",
            'gender': "Belgilanmagan",
            'age': getattr(user, 'age', 0),
            'region': getattr(user, 'region', 'Noma\'lum'),
            'profession': getattr(user, 'profession', 'Noma\'lum'),
            'registration_date': "Noma'lum",
            'level': getattr(user, 'level', '0-bosqich'),
            'referral_count': 0,
            'is_confirmed': False
        }
    


@sync_to_async
def get_user_profile_by_telegram_id(telegram_id: str):
    """
    Barcha kerakli user ma'lumotlarini dict ko'rinishida qaytaradi.
    - Barcha ORM ishlari bu sync_to_async ichida bajariladi.
    """
    try:
        user = TelegramUser.objects.select_related('invited_by').filter(telegram_id=telegram_id).first()
        if not user:
            return None

        invited = user.invited_by
        invited_data = None
        if invited:
            invited_data = {
                "telegram_id": getattr(invited, "telegram_id", None),
                "full_name": getattr(invited, "full_name", None),
                "telegram_username": getattr(invited, "telegram_username", None)
            }

        return {
            'full_name': user.full_name,
            'telegram_id': str(user.telegram_id),
            'phone': user.phone_number or "Mavjud emas",
            'username': f"@{user.telegram_username}" if user.telegram_username else "mavjud emas",
            'gender': "Erkak" if user.gender == "M" else "Ayol" if user.gender == "F" else "Belgilanmagan",
            'age': getattr(user, 'age', "Noma'lum"),
            'region': getattr(user, 'region', "Noma'lum"),
            'profession': getattr(user, 'profession', "Noma'lum"),
            'registration_date': user.registration_date.strftime('%d.%m.%Y %H:%M') if user.registration_date else "Noma'lum",
            'level': getattr(user, 'level', '0-bosqich'),
            'referral_count': getattr(user, 'referral_count', 0),
            'is_confirmed': bool(user.is_confirmed),
            'invited_by': invited_data
        }
    except Exception as e:
        print(f"[selectors.get_user_profile_by_telegram_id] Error: {e}")
        return None


@sync_to_async
def get_referrer_display_by_telegram_id(inviter_telegram_id: str):
    """
    Inviter telegram_id bo'yicha display string qaytaradi (masalan: 'Ism (@username)') yoki "Yo'q".
    """
    try:
        if not inviter_telegram_id:
            return "Yo'q"

        inviter = TelegramUser.objects.filter(telegram_id=inviter_telegram_id).first()
        if not inviter:
            return "Yo'q"
        if inviter.telegram_username:
            return f"{inviter.full_name} (@{inviter.telegram_username})"
        return inviter.full_name
    except Exception as e:
        print(f"[selectors.get_referrer_display_by_telegram_id] Error: {e}")
        return "Yo'q"


@sync_to_async
def get_course_for_next_level_by_user_level(user_level: str):
    """
    user_level (masalan '7-bosqich' yoki 'level_7') ga qarab keyingi kursni qaytaradi.
    Return: dict {'id': ..., 'name': ...} yoki None
    """
    try:
        # normalize
        if not user_level:
            user_level = "0-bosqich"
        if user_level.startswith("level_"):
            # level_1 -> 1-bosqich
            try:
                num = user_level.split("_")[1]
                user_level = f"{num}-bosqich"
            except Exception:
                user_level = "0-bosqich"

        try:
            current_num = int(user_level.split("-")[0])
        except Exception:
            current_num = 0

        # agar 7-dan yuqori bo'lsa birinchi faol kursni qaytaramiz
        if current_num > 6:
            course = Kurslar.objects.filter(is_active=True).order_by('-created_at').first()
        else:
            next_level_num = current_num + 1
            next_level = f"{next_level_num}-bosqich"
            course_level_field = LEVEL_MAPPING.get(next_level, next_level)
            course = Kurslar.objects.filter(is_active=True, level=course_level_field).order_by('-created_at').first()

        if not course:
            return None

        return {
            "id": course.id,
            "name": getattr(course, "name", "Noma'lum")
        }
    except Exception as e:
        print(f"[selectors.get_course_for_next_level_by_user_level] Error: {e}")
        return None


@sync_to_async
def get_referral_link_for_user(telegram_id: str):
    """
    Tegishli referal linkni qaytaradi. Agar modelda get_referral_link method bo'lsa undan foydalanadi,
    aks holda statik link yasaydi.
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={telegram_id}"

        # prefer model method if exists (kiritilgan bo'lsa)
        if hasattr(user, "get_referral_link"):
            try:
                return user.get_referral_link()
            except Exception:
                pass

        return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={telegram_id}"
    except Exception as e:
        print(f"[selectors.get_referral_link_for_user] Error: {e}")
        return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={telegram_id}"
    
@sync_to_async
def get_gifts_is_active():
    """
    Faol sovg'alarni olish
    """
    try:
        return list(Gifts.objects.filter(is_active=True).order_by('-created_at'))
    except Exception as e:
        print(f"[selectors.get_gifts_is_active] Error: {e}")
        return []