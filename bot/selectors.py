import uuid
from datetime import datetime
from asgiref.sync import sync_to_async

from django.db.models import Q, Count
from core.settings import TELEGRAM_BOT_USERNAME
from .models import (
    TelegramUser,
    MandatoryChannel,
    Payments,
    Kurslar,
    ReferralPayment,
    Gifts,
)
from bot.services.notification import (
    notify_new_referral,
    notify_referrer_changed,
    notify_referrer_warning,
    notify_referral_removed,
)


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
    return list(
        TelegramUser.objects.filter(is_admin=True).values_list("telegram_id", flat=True)
    )


@sync_to_async
def get_all_channels():
    """Barcha majburiy kanallarni olish"""
    return list(MandatoryChannel.objects.filter(is_active=True))


@sync_to_async
def get_user_active_payments(user_id):
    """Foydalanuvchining faol (tasdiqlangan va muddati tugamagan) to'lovlarini olish"""
    return list(
        Payments.objects.filter(
            Q(user__telegram_id=user_id),
            Q(status="CONFIRMED"),
            Q(course__isnull=False) & Q(course__is_active=True),
        ).select_related("course")
    )


@sync_to_async
def get_active_kurslar():
    """Faol kurslarni olish"""
    return list(Kurslar.objects.filter(is_active=True).order_by("-created_at"))


@sync_to_async
def get_kurs_details(kurs_id):
    """Kurs tafsilotlarini olish"""
    return Kurslar.objects.filter(id=kurs_id).first()


@sync_to_async
def create_payment_request(
    user_id, payment_type, amount, kurs_id=None, photo_path=None
):
    """Yangi to'lov so'rovini yaratish"""
    user = TelegramUser.objects.filter(telegram_id=user_id).first()
    if not user:
        return None

    payment = Payments(
        user=user, payment_type=payment_type, amount=amount, status="PENDING"
    )

    if payment_type == "COURSE" and kurs_id:
        payment.course = Kurslar.objects.filter(id=kurs_id).first()

    if photo_path:
        payment.payment_screenshot = photo_path

    payment.save()
    return payment


@sync_to_async
def get_kurs_participants_count(kurs_id):
    """Kurs ishtirokchilari sonini olish"""
    return (
        Payments.objects.filter(course_id=kurs_id, status="CONFIRMED")
        .values("user")
        .distinct()
        .count()
    )


@sync_to_async
def confirm_payment(payment_id, admin_user_id):
    """To'lovni tasdiqlash"""
    payment = Payments.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()

    if payment and admin_user:
        payment.status = "CONFIRMED"
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
        payment.status = "REJECTED"
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
        user__telegram_id=telegram_id, course__isnull=False, status="CONFIRMED"
    ).exists()


@sync_to_async
def get_all_active_courses():
    """
    Barcha faol kurslarni olish (QuerySet).
    """
    return Kurslar.objects.filter(is_active=True).order_by("-created_at")


@sync_to_async
def get_first_active_course():
    """Birinchi faol kursni olish"""
    return Kurslar.objects.filter(is_active=True).order_by("-created_at").first()


@sync_to_async
def get_all_active_courses_list():
    """
    Barcha faol kurslarni olish - list qaytaradi, QuerySet emas
    """
    return list(Kurslar.objects.filter(is_active=True).order_by("-created_at"))


@sync_to_async
def get_course_by_user_level(user_level: str):
    """
    Foydalanuvchi leveliga mos birinchi faol kursni olish
    """
    try:
        # User level formatini tekshirish va to'g'rilash
        if user_level.startswith("level_"):
            # Agar level_1 formatida bo'lsa, uni 1-bosqich formatiga o'tkazish
            level_num = user_level.split("_")[1]
            user_level = f"{level_num}-bosqich"

        # User level-ini int ga o'tkazamiz
        user_level_int = int(user_level.split("-")[0])

        # Agar user level 7 dan katta bo'lsa, birinchi faol kursni qaytaramiz
        if user_level_int > 6:
            print(
                f"User level {user_level} dan yuqori, birinchi faol kurs qaytariladi."
            )
            return (
                Kurslar.objects.filter(is_active=True).order_by("-created_at").first()
            )

        # Keyingi bosqich nomini aniqlaymiz
        next_level_int = user_level_int + 1
        next_level = f"{next_level_int}-bosqich"

        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(next_level, next_level)
        print(
            f"Looking for course for user level: {user_level}, mapped to course level: {course_level}"
        )

        # Faqat shu levelga mos faol kursni olish
        course = (
            Kurslar.objects.filter(is_active=True, level=course_level)
            .order_by("-created_at")
            .first()
        )

        if course:
            print(f"Found course for level {course_level}: {course.name}")
        else:
            print(
                f"No course found for level: {course_level}, returning first active course"
            )
            course = (
                Kurslar.objects.filter(is_active=True).order_by("-created_at").first()
            )

        return course
    except Exception as e:
        print(f"Error getting course by user level: {e}")
        return Kurslar.objects.filter(is_active=True).order_by("-created_at").first()


@sync_to_async
def get_user_level(telegram_id):
    """
    Foydalanuvchini levelini olish va formatini to'g'rilash
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
        if user and user.level:
            # Level formatini tekshirish va to'g'rilash
            if user.level.startswith("level_"):
                # level_1 -> 1-bosqich
                level_num = user.level.split("_")[1]
                corrected_level = f"{level_num}-bosqich"
                print(
                    f"User found: {user.full_name}, Level: {user.level} -> corrected to: {corrected_level}"
                )
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
        if level.startswith("level_"):
            level_num = level.split("_")[1]
            level = f"{level_num}-bosqich"

        # User level-ini int ga o'tkazamiz
        user_level_int = int(level.split("-")[0])

        # Keyingi bosqich nomini aniqlaymiz
        next_level_int = user_level_int + 1
        next_level = f"{next_level_int}-bosqich"

        # User level-ini course level formatiga o'girish
        course_level = LEVEL_MAPPING.get(next_level, next_level)
        print(
            f"Looking for course with user level: {level}, mapped to course level: {course_level}"
        )

        course = (
            Kurslar.objects.filter(is_active=True, level=course_level)
            .order_by("-created_at")
            .first()
        )

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
            user__telegram_id=telegram_id, course__isnull=False, status="CONFIRMED"
        ).select_related("course")

        purchased_course_levels = set()
        for payment in payments:
            if payment.course and payment.course.level:
                print(
                    f"Found purchased course: {payment.course.name}, Level: {payment.course.level}"
                )

                # Course level ni user level formatiga o'girish
                course_level = REVERSE_LEVEL_MAPPING.get(
                    payment.course.level, payment.course.level
                )
                if course_level:
                    try:
                        # Course level formatini tekshirish
                        if course_level.startswith("level_"):
                            level_num = course_level.split("_")[1]
                            course_level = f"{level_num}-bosqich"

                        purchased_level_num = int(course_level.split("-")[0])
                        purchased_course_levels.add(purchased_level_num)
                        print(f"Added level {purchased_level_num} to purchased levels")
                    except (ValueError, AttributeError) as e:
                        print(
                            f"Error processing course level {payment.course.level}: {e}"
                        )
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
        if user_level.startswith("level_"):
            level_num = user_level.split("_")[1]
            user_level = f"{level_num}-bosqich"

        # Foydalanuvchining hozirgi level raqamini olish
        try:
            current_level_num = int(user_level.split("-")[0])
            target_level_num = int(target_level.split("-")[0])
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
                status="CONFIRMED",
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
def get_root_referrer(user_id: str):
    """Optimized version of get_root_referrer"""
    try:
        user = (
            TelegramUser.objects.only("invited_by").filter(telegram_id=user_id).first()
        )
        if not user or not user.invited_by:
            return None

        invited_by = user.invited_by

        if invited_by.invited_by:
            return invited_by.invited_by

        return invited_by
    except Exception as e:
        print(f"[get_root_referrer] Error: {e}")
        return None


@sync_to_async
def create_referral_payment_request(user_id: str, amount: float):
    """Referral to'lov so'rovini yaratish (Root referrer bilan)"""
    try:
        print(
            f"[create_referral_payment] Creating payment for user {user_id}, amount {amount}"
        )

        user = TelegramUser.objects.filter(telegram_id=user_id).first()
        if not user:
            print(f"[create_referral_payment] User {user_id} not found")
            return None

        print(f"[create_referral_payment] User found: {user.full_name}")

        # Root referrer-ni topish
        invited_user = user.invited_by
        if invited_user:
            if invited_user.invited_by:
                root_referrer = invited_user.invited_by
            else:
                root_referrer = invited_user

            payment = ReferralPayment.objects.create(
                user=user,
                referrer=root_referrer,
                amount=amount,
                payment_type="REFERRAL_BONUS",
                status="PENDING",
            )

            return payment

    except Exception as e:
        print(f"[create_referral_payment] Error: {e}")
        import traceback

        print(f"[create_referral_payment] Traceback: {traceback.format_exc()}")
        return None


@sync_to_async
def get_user_referral_network_stats(user_id: str) -> dict:
    """Foydalanuvchining butun referral tarmog'i bo'yicha statistika"""
    # To'g'ridan-to'g'ri referrallar
    direct = TelegramUser.objects.filter(invited_by__telegram_id=user_id)

    # Butun tarmoq (rekursiv)
    def get_network_count(parent_id: str):
        count = 0
        children = TelegramUser.objects.filter(invited_by__telegram_id=parent_id)
        for child in children:
            count += 1 + get_network_count(child.telegram_id)
        return count

    total_network = get_network_count(user_id)

    return {
        "direct_referrals": direct.count(),
        "total_network": total_network,
        "active_in_network": TelegramUser.objects.filter(invited_by__in=direct).count(),
    }


@sync_to_async
def get_referral_network_payments(user_id: str):
    """Foydalanuvchining butun tarmog'idan kelgan to'lovlar"""
    # Faqat root referrer uchun ishlaydi
    return list(
        ReferralPayment.objects.filter(
            referrer__telegram_id=user_id, payment_type="REFERRAL_BONUS"
        ).order_by("-created_at")
    )


@sync_to_async
def get_referral_network_tree(user_id: str, depth: int = 5):
    """Butun referral tarmog'ini ko'rish"""

    def build_tree(parent_id: str, current_depth: int = 0):
        if current_depth >= depth:
            return []

        children = TelegramUser.objects.filter(
            invited_by__telegram_id=parent_id
        ).order_by("-registration_date")

        result = []
        for child in children:
            child_data = {
                "user": child,
                "level": current_depth + 1,
                "children": build_tree(child.telegram_id, current_depth + 1),
            }
            result.append(child_data)

        return result

    return {
        "root": TelegramUser.objects.get(telegram_id=user_id),
        "tree": build_tree(user_id),
    }


# Updated referral functions with root logic
@sync_to_async
def get_user_referrals(user_id: str, limit: int = 8, offset: int = 0):
    """Foydalanuvchining to'g'ridan-to'g'ri referallarini olish"""
    return list(
        TelegramUser.objects.filter(invited_by__telegram_id=user_id).order_by(
            "-registration_date"
        )[offset : offset + limit]
    )


@sync_to_async
def get_user_referrals_count(user_id: str) -> int:
    """Foydalanuvchining to'g'ridan-to'g'ri referallari sonini olish"""
    return TelegramUser.objects.filter(invited_by__telegram_id=user_id).count()


@sync_to_async
def get_confirmed_referrals_count(user_id: str) -> int:
    """Foydalanuvchining tasdiqlangan to'g'ridan-to'g'ri referallari sonini olish"""
    return TelegramUser.objects.filter(
        invited_by__telegram_id=user_id, is_confirmed=True
    ).count()


@sync_to_async
def get_monthly_referrals_count(user_id: str) -> int:
    """Bu oy qo'shilgan to'g'ridan-to'g'ri referallar sonini olish"""
    start_of_month = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return TelegramUser.objects.filter(
        invited_by__telegram_id=user_id, registration_date__gte=start_of_month
    ).count()


@sync_to_async
def get_referrals_by_level(user_id: str) -> dict:
    """To'g'ridan-to'g'ri referallarni daraja bo'yicha guruplash"""
    referrals = (
        TelegramUser.objects.filter(invited_by__telegram_id=user_id)
        .values("level")
        .annotate(count=Count("level"))
        .order_by("level")
    )

    result = {}
    for item in referrals:
        level = item["level"] or "0-bosqich"
        result[level] = item["count"]

    return result


@sync_to_async
def get_user_referral_tree(user_id: str, depth: int = 3):
    """Referallar daraxtini olish (chuqurlik bilan)"""

    def build_tree(parent_id: str, current_depth: int = 0):
        if current_depth >= depth:
            return []

        children = TelegramUser.objects.filter(
            invited_by__telegram_id=parent_id
        ).order_by("-registration_date")

        result = []
        for child in children:
            child_data = {
                "user": child,
                "children": build_tree(child.telegram_id, current_depth + 1),
            }
            result.append(child_data)

        return result

    return build_tree(user_id)


@sync_to_async
def get_user_referral_levels_stats(user_id: str) -> dict:
    """Foydalanuvchining butun tarmoq referallari bo'yicha batafsil statistika"""
    # 1-daraja referallar (to'g'ridan-to'g'ri)
    level_1 = TelegramUser.objects.filter(invited_by__telegram_id=user_id)

    # 2-daraja referallar
    level_2 = TelegramUser.objects.filter(invited_by__invited_by__telegram_id=user_id)

    # 3-daraja referallar
    level_3 = TelegramUser.objects.filter(
        invited_by__invited_by__invited_by__telegram_id=user_id
    )

    # 4-daraja referallar
    level_4 = TelegramUser.objects.filter(
        invited_by__invited_by__invited_by__invited_by__telegram_id=user_id
    )

    # 5-daraja referallar
    level_5 = TelegramUser.objects.filter(
        invited_by__invited_by__invited_by__invited_by__invited_by__telegram_id=user_id
    )

    return {
        "level_1": level_1.count(),
        "level_2": level_2.count(),
        "level_3": level_3.count(),
        "level_4": level_4.count(),
        "level_5": level_5.count(),
        "total": level_1.count()
        + level_2.count()
        + level_3.count()
        + level_4.count()
        + level_5.count(),
    }


@sync_to_async
def get_top_referrers(limit: int = 10):
    """Eng ko'p to'g'ridan-to'g'ri referalga ega foydalanuvchilar"""
    return list(
        TelegramUser.objects.annotate(referral_count_db=Count("referrals"))
        .filter(referral_count_db__gt=0)
        .order_by("-referral_count_db")[:limit]
    )


@sync_to_async
def search_referrals(user_id: str, search_query: str, limit: int = 10):
    """To'g'ridan-to'g'ri referallar orasida qidirish"""
    return list(
        TelegramUser.objects.filter(invited_by__telegram_id=user_id)
        .filter(
            Q(full_name__icontains=search_query)
            | Q(phone_number__icontains=search_query)
            | Q(telegram_username__icontains=search_query)
        )
        .order_by("-registration_date")[:limit]
    )


@sync_to_async
def get_pending_referral_payments(referrer_id: str):
    """Root referrer uchun tasdiqlanishi kerak bo'lgan referral to'lovlarni olish"""
    return list(
        ReferralPayment.objects.filter(
            referrer__telegram_id=referrer_id,
            payment_type="REFERRAL_BONUS",
            status="PENDING",
        )
    )


@sync_to_async
def confirm_referral_payment(payment_id: str, admin_user_id: str):
    """Referral to'lovni tasdiqlash"""
    payment = ReferralPayment.objects.filter(id=payment_id).first()
    admin_user = TelegramUser.objects.filter(telegram_id=admin_user_id).first()

    if payment and admin_user:
        payment.status = "CONFIRMED"
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
        payment.status = "REJECTED"
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
        if hasattr(user_info, "get_referral_link"):
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
        user.save(update_fields=["card_number", "card_holder_full_name"])
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
        return user.registration_date.strftime("%d.%m.%Y %H:%M")
    return "Noma'lum"


@sync_to_async
def get_user_level_safe(user):
    """User level-ni async olish"""
    return user.level


@sync_to_async
def get_user_referral_count_safe(user):
    """User referral count-ni async olish"""
    return getattr(user, "referral_count", 0)


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
            "is_confirmed",
        ).get(pk=user.pk)

        return {
            "full_name": user.full_name,
            "telegram_id": user.telegram_id,
            "phone": user.phone_number or "Mavjud emas",
            "username": (
                f"@{user.telegram_username}"
                if user.telegram_username
                else "mavjud emas"
            ),
            "gender": (
                "Erkak"
                if user.gender == "M"
                else "Ayol" if user.gender == "F" else "Belgilanmagan"
            ),
            "age": user.age,
            "region": user.region,
            "profession": user.profession,
            "registration_date": (
                user.registration_date.strftime("%d.%m.%Y %H:%M")
                if user.registration_date
                else "Noma'lum"
            ),
            "level": user.level,
            "referral_count": getattr(user, "referral_count", 0),
            "is_confirmed": user.is_confirmed,
        }
    except Exception as e:
        print(f"Error in get_user_profile_data: {e}")
        return {
            "full_name": getattr(user, "full_name", "Noma'lum"),
            "telegram_id": getattr(user, "telegram_id", ""),
            "phone": "Mavjud emas",
            "username": "mavjud emas",
            "gender": "Belgilanmagan",
            "age": getattr(user, "age", 0),
            "region": getattr(user, "region", "Noma'lum"),
            "profession": getattr(user, "profession", "Noma'lum"),
            "registration_date": "Noma'lum",
            "level": getattr(user, "level", "0-bosqich"),
            "referral_count": 0,
            "is_confirmed": False,
        }


@sync_to_async
def get_user_profile_by_telegram_id(telegram_id: str):
    """
    Barcha kerakli user ma'lumotlarini dict ko'rinishida qaytaradi.
    - Barcha ORM ishlari bu sync_to_async ichida bajariladi.
    """
    try:
        user = (
            TelegramUser.objects.select_related("invited_by")
            .filter(telegram_id=telegram_id)
            .first()
        )
        if not user:
            return None

        invited = user.invited_by
        invited_data = None
        if invited:
            invited_data = {
                "telegram_id": getattr(invited, "telegram_id", None),
                "full_name": getattr(invited, "full_name", None),
                "telegram_username": getattr(invited, "telegram_username", None),
            }

        return {
            "full_name": user.full_name,
            "telegram_id": str(user.telegram_id),
            "phone": user.phone_number or "Mavjud emas",
            "username": (
                f"@{user.telegram_username}"
                if user.telegram_username
                else "mavjud emas"
            ),
            "gender": (
                "Erkak"
                if user.gender == "M"
                else "Ayol" if user.gender == "F" else "Belgilanmagan"
            ),
            "age": getattr(user, "age", "Noma'lum"),
            "region": getattr(user, "region", "Noma'lum"),
            "profession": getattr(user, "profession", "Noma'lum"),
            "registration_date": (
                user.registration_date.strftime("%d.%m.%Y %H:%M")
                if user.registration_date
                else "Noma'lum"
            ),
            "level": getattr(user, "level", "0-bosqich"),
            "referral_count": getattr(user, "referral_count", 0),
            "is_confirmed": bool(user.is_confirmed),
            "invited_by": invited_data,
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
            return f"{inviter.full_name} ({inviter.telegram_username})"
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
            course = (
                Kurslar.objects.filter(is_active=True).order_by("-created_at").first()
            )
        else:
            next_level_num = current_num + 1
            next_level = f"{next_level_num}-bosqich"
            course_level_field = LEVEL_MAPPING.get(next_level, next_level)
            course = (
                Kurslar.objects.filter(is_active=True, level=course_level_field)
                .order_by("-created_at")
                .first()
            )

        if not course:
            return None

        return {"id": course.id, "name": getattr(course, "name", "Noma'lum")}
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
        return list(Gifts.objects.filter(is_active=True).order_by("-created_at"))
    except Exception as e:
        print(f"[selectors.get_gifts_is_active] Error: {e}")
        return []


# Referal foydalanuvchilarni tekshirish
def compare_levels(level1: str, level2: str) -> int:
    """
    Levellarni solishtirish funksiyasi
    Returns:
        1 agar level1 > level2
        0 agar level1 == level2
        -1 agar level1 < level2
    """

    def extract_level_number(level: str) -> int:
        try:
            if level.startswith("level_"):
                return int(level.split("_")[1])
            elif "-bosqich" in level:
                return int(level.split("-")[0])
            return 0
        except (ValueError, IndexError):
            return 0

    num1 = extract_level_number(level1)
    num2 = extract_level_number(level2)

    if num1 > num2:
        return 1
    elif num1 == num2:
        return 0
    else:
        return -1


@sync_to_async
def check_and_handle_referrer_level_advancement(user_telegram_id: str):
    """
    Foydalanuvchi darajasi refereridan yuqori bo'lsa,
    admin uchun vakolatlarni tekshiradi va kerakli harakatlarni bajaradi

    Returns:
        dict: {
            'needs_replacement': bool,
            'current_referrer': dict or None,
            'notification_sent': bool,
            'message': str
        }
    """
    try:
        # Foydalanuvchini topish
        user = (
            TelegramUser.objects.select_related("invited_by")
            .filter(telegram_id=user_telegram_id)
            .first()
        )

        if not user:
            return {
                "needs_replacement": False,
                "current_referrer": None,
                "notification_sent": False,
                "message": "Foydalanuvchi topilmadi",
            }

        # Agar referrer yo'q bo'lsa
        if not user.invited_by:
            return {
                "needs_replacement": False,
                "current_referrer": None,
                "notification_sent": False,
                "message": "Foydalanuvchining referreri mavjud emas",
            }

        referrer = user.invited_by

        # Levellarni solishtirish
        level_comparison = compare_levels(user.level, referrer.level)

        if level_comparison <= 0:
            # User darajasi referrer darajasidan kichik yoki teng
            return {
                "needs_replacement": False,
                "current_referrer": {
                    "telegram_id": referrer.telegram_id,
                    "full_name": referrer.full_name,
                    "level": referrer.level,
                },
                "notification_sent": False,
                "message": "Referrer darajasi mos, almashtirish kerak emas",
            }

        # User darajasi referrerdan yuqori - almashtirish kerak
        return {
            "needs_replacement": True,
            "current_referrer": {
                "telegram_id": referrer.telegram_id,
                "full_name": referrer.full_name,
                "level": referrer.level,
                "telegram_username": referrer.telegram_username,
            },
            "user_data": {
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "level": user.level,
            },
            "notification_sent": True,  # Bu async task bilan yuboriladi
            "message": f"Foydalanuvchi {user.full_name} darajasi ({user.level}) referrer {referrer.full_name} darajasidan ({referrer.level}) yuqori. Almashtirish kerak!",
        }

    except Exception as e:
        print(f"Error in check_and_handle_referrer_level_advancement: {e}")
        return {
            "needs_replacement": False,
            "current_referrer": None,
            "notification_sent": False,
            "message": f"Xatolik yuz berdi: {str(e)}",
        }


async def send_referrer_warning_notification(
    referrer_telegram_id: str,
    advanced_user_name: str,
    advanced_user_level: str,
    referrer_level: str,
):
    """
    Referrerga ogohlantirish xabarini Telegram API orqali yuborish
    """
    try:
        result = await notify_referrer_warning(
            referrer_telegram_id,
            advanced_user_name,
            advanced_user_level,
            referrer_level,
        )

        if result["success"]:
            print(
                f"Warning notification sent successfully to referrer {referrer_telegram_id}"
            )
            return True
        else:
            print(
                f"Failed to send warning notification to referrer {referrer_telegram_id}: {result['error']}"
            )
            return False

    except Exception as e:
        print(f"Error sending warning notification: {e}")
        return False


@sync_to_async
def replace_referrer_by_admin(
    user_telegram_id: str, new_referrer_telegram_id: str, admin_telegram_id: str
):
    """
    Admin tomonidan referrerni almashtirish

    Args:
        user_telegram_id: Foydalanuvchi telegram ID
        new_referrer_telegram_id: Yangi referrer telegram ID
        admin_telegram_id: Admin telegram ID

    Returns:
        dict: Amaliyot natijasi
    """
    try:
        # Foydalanuvchini topish
        user = (
            TelegramUser.objects.select_related("invited_by")
            .filter(telegram_id=user_telegram_id)
            .first()
        )

        if not user:
            return {"success": False, "message": "Foydalanuvchi topilmadi"}

        # Yangi referrerni topish
        new_referrer = TelegramUser.objects.filter(
            telegram_id=new_referrer_telegram_id
        ).first()

        if not new_referrer:
            return {"success": False, "message": "Yangi referrer topilmadi"}

        # Adminni tekshirish
        admin = TelegramUser.objects.filter(
            telegram_id=admin_telegram_id, is_admin=True
        ).first()

        if not admin:
            return {
                "success": False,
                "message": "Admin huquqi yo'q yoki admin topilmadi",
            }

        # Yangi referrer darajasi foydalanuvchi darajasidan yuqori yoki teng ekanligini tekshirish
        level_comparison = compare_levels(new_referrer.level, user.level)
        if level_comparison < 0:
            return {
                "success": False,
                "message": f"Yangi referrer darajasi ({new_referrer.level}) foydalanuvchi darajasidan ({user.level}) past",
            }

        # Eski referrer ma'lumotlarini saqlash
        old_referrer = user.invited_by
        old_referrer_data = None
        if old_referrer:
            old_referrer_data = {
                "telegram_id": old_referrer.telegram_id,
                "full_name": old_referrer.full_name,
                "level": old_referrer.level,
            }

        # Referrerni almashtirish
        user.invited_by = new_referrer
        user.save(update_fields=["invited_by"])

        # Yangi referrerning referral_count ni yangilash
        new_referrer.update_referral_count()

        # Eski referrerning referral_count ni yangilash
        if old_referrer:
            old_referrer.update_referral_count()

        return {
            "success": True,
            "message": "Referrer muvaffaqiyatli almashtirildi",
            "old_referrer": old_referrer_data,
            "new_referrer": {
                "telegram_id": new_referrer.telegram_id,
                "full_name": new_referrer.full_name,
                "level": new_referrer.level,
            },
            "user_data": {
                "telegram_id": user.telegram_id,
                "full_name": user.full_name,
                "level": user.level,
            },
            "admin": {"telegram_id": admin.telegram_id, "full_name": admin.full_name},
        }

    except Exception as e:
        print(f"Error in replace_referrer_by_admin: {e}")
        return {"success": False, "message": f"Xatolik yuz berdi: {str(e)}"}


async def send_referrer_replacement_notifications(replacement_result: dict):
    """
    Referrer almashtirish natijasida barcha tegishli xabarlarni yuborish
    """
    if not replacement_result["success"]:
        return {
            "user_notified": False,
            "new_referrer_notified": False,
            "old_referrer_notified": False,
            "error": "Replacement was not successful",
        }

    user_data = replacement_result["user_data"]
    new_referrer = replacement_result["new_referrer"]
    old_referrer = replacement_result.get("old_referrer")
    admin = replacement_result["admin"]

    notification_results = {
        "user_notified": False,
        "new_referrer_notified": False,
        "old_referrer_notified": False,
    }

    try:
        # 1. Foydalanuvchiga xabar yuborish
        old_referrer_name = old_referrer["full_name"] if old_referrer else "Noma'lum"
        user_result = await notify_referrer_changed(
            user_data["telegram_id"],
            old_referrer_name,
            new_referrer["full_name"],
            admin["full_name"],
        )
        notification_results["user_notified"] = user_result["success"]

        # 2. Yangi referrerga xabar yuborish
        new_referrer_result = await notify_new_referral(
            new_referrer["telegram_id"],
            user_data["full_name"],
            user_data["level"],
            admin["full_name"],
        )
        notification_results["new_referrer_notified"] = new_referrer_result["success"]

        # 3. Eski referrerga xabar yuborish (agar mavjud bo'lsa)
        if old_referrer:
            old_referrer_result = await notify_referral_removed(
                old_referrer["telegram_id"],
                user_data["full_name"],
                user_data["level"],
                admin["full_name"],
            )
            notification_results["old_referrer_notified"] = old_referrer_result[
                "success"
            ]
        else:
            notification_results["old_referrer_notified"] = True  # Eski referrer yo'q

    except Exception as e:
        print(f"Error sending referrer replacement notifications: {e}")
        notification_results["error"] = str(e)

    return notification_results


@sync_to_async
def get_users_needing_referrer_replacement():
    """
    Referreri almashtirilishi kerak bo'lgan foydalanuvchilarni topish
    """
    try:
        users_needing_replacement = []

        # Referer-i bor foydalanuvchilarni olish
        users_with_referrers = TelegramUser.objects.select_related("invited_by").filter(
            invited_by__isnull=False
        )

        for user in users_with_referrers:
            referrer = user.invited_by
            level_comparison = compare_levels(user.level, referrer.level)

            if level_comparison > 0:  # User darajasi referrerdan yuqori
                users_needing_replacement.append(
                    {
                        "user": {
                            "telegram_id": user.telegram_id,
                            "full_name": user.full_name,
                            "level": user.level,
                        },
                        "current_referrer": {
                            "telegram_id": referrer.telegram_id,
                            "full_name": referrer.full_name,
                            "level": referrer.level,
                        },
                    }
                )

        return {
            "success": True,
            "count": len(users_needing_replacement),
            "users": users_needing_replacement,
        }

    except Exception as e:
        print(f"Error in get_users_needing_referrer_replacement: {e}")
        return {"success": False, "count": 0, "users": [], "error": str(e)}


@sync_to_async
def find_suitable_referrers_for_user(user_telegram_id: str, limit: int = 10):
    """
    Foydalanuvchi uchun mos referrerlarni topish
    (Daraja bir xil yoki yuqori bo'lgan foydalanuvchilar)
    """
    try:
        user = TelegramUser.objects.filter(telegram_id=user_telegram_id).first()
        if not user:
            return {
                "success": False,
                "suitable_referrers": [],
                "message": "Foydalanuvchi topilmadi",
            }

        # Foydalanuvchi darajasidan yuqori yoki teng darajadagi foydalanuvchilarni topish
        user_level_num = 0
        try:
            if user.level.startswith("level_"):
                user_level_num = int(user.level.split("_")[1])
            elif "-bosqich" in user.level:
                user_level_num = int(user.level.split("-")[0])
        except (ValueError, IndexError):
            user_level_num = 0

        suitable_referrers = []

        # Barcha foydalanuvchilarni tekshirish
        all_users = TelegramUser.objects.exclude(telegram_id=user_telegram_id).filter(
            is_confirmed=True
        )[
            :100
        ]  # Performance uchun limit

        for potential_referrer in all_users:
            referrer_level_num = 0
            try:
                if potential_referrer.level.startswith("level_"):
                    referrer_level_num = int(potential_referrer.level.split("_")[1])
                elif "-bosqich" in potential_referrer.level:
                    referrer_level_num = int(potential_referrer.level.split("-")[0])
            except (ValueError, IndexError):
                referrer_level_num = 0

            # Agar potential referrer darajasi user darajasidan yuqori yoki teng bo'lsa
            if referrer_level_num >= user_level_num:
                suitable_referrers.append(
                    {
                        "telegram_id": potential_referrer.telegram_id,
                        "full_name": potential_referrer.full_name,
                        "level": potential_referrer.level,
                        "level_number": referrer_level_num,
                        "referral_count": potential_referrer.referral_count,
                        "telegram_username": potential_referrer.telegram_username,
                    }
                )

        # Darajaga ko'ra saralash (yuqori darajalilar birinchi)
        suitable_referrers.sort(
            key=lambda x: (-x["level_number"], -x["referral_count"])
        )

        return {
            "success": True,
            "suitable_referrers": suitable_referrers[:limit],
            "total_found": len(suitable_referrers),
            "user_level": user.level,
        }

    except Exception as e:
        print(f"Error in find_suitable_referrers_for_user: {e}")
        return {
            "success": False,
            "suitable_referrers": [],
            "message": f"Xatolik: {str(e)}",
        }


# Asosiy workflow funksiyalari


async def handle_user_level_advancement_workflow(user_telegram_id: str):
    """
    Foydalanuvchi darajasi oshganda to'liq workflow ni bajarish

    1. Referrer darajasini tekshirish
    2. Agar kerak bo'lsa ogohlantirish yuborish
    3. Natijani qaytarish
    """
    try:
        # 1. Darajani tekshirish
        check_result = await check_and_handle_referrer_level_advancement(
            user_telegram_id
        )

        if not check_result["needs_replacement"]:
            return check_result

        # 2. Referrerga ogohlantirish yuborish
        referrer_data = check_result["current_referrer"]
        user_data = check_result["user_data"]

        warning_sent = await send_referrer_warning_notification(
            referrer_data["telegram_id"],
            user_data["full_name"],
            user_data["level"],
            referrer_data["level"],
        )

        check_result["notification_sent"] = warning_sent

        if warning_sent:
            check_result["message"] += " Referrerga ogohlantirish yuborildi."
        else:
            check_result["message"] += " Referrerga ogohlantirish yuborishda xatolik."

        return check_result

    except Exception as e:
        print(f"Error in handle_user_level_advancement_workflow: {e}")
        return {
            "needs_replacement": False,
            "current_referrer": None,
            "notification_sent": False,
            "message": f"Workflow xatoligi: {str(e)}",
        }


async def complete_referrer_replacement_workflow(
    user_telegram_id: str, new_referrer_telegram_id: str, admin_telegram_id: str
):
    """
    To'liq referrer almashtirish workflow ni bajarish

    1. Referrerni almashtirish
    2. Barcha tegishli xabarlarni yuborish
    3. Natijani qaytarish
    """
    try:
        # 1. Referrerni almashtirish
        replacement_result = await replace_referrer_by_admin(
            user_telegram_id, new_referrer_telegram_id, admin_telegram_id
        )

        if not replacement_result["success"]:
            return {
                "replacement_success": False,
                "notifications_sent": False,
                "message": replacement_result["message"],
            }

        # 2. Xabarlarni yuborish
        notification_results = await send_referrer_replacement_notifications(
            replacement_result
        )

        return {
            "replacement_success": True,
            "notifications_sent": True,
            "notification_details": notification_results,
            "replacement_data": replacement_result,
            "message": "Referrer muvaffaqiyatli almashtirildi va barcha xabarlar yuborildi",
        }

    except Exception as e:
        print(f"Error in complete_referrer_replacement_workflow: {e}")
        return {
            "replacement_success": False,
            "notifications_sent": False,
            "message": f"Workflow xatoligi: {str(e)}",
        }


# Utility funksiyalar


async def bulk_check_referrer_levels():
    """
    Barcha foydalanuvchilarning referrer darajalarini tekshirish
    """
    try:
        users_needing_replacement = await get_users_needing_referrer_replacement()

        if not users_needing_replacement["success"]:
            return users_needing_replacement

        warning_results = []

        for user_info in users_needing_replacement["users"]:
            user_data = user_info["user"]
            referrer_data = user_info["current_referrer"]

            # Har bir referrerga ogohlantirish yuborish
            warning_sent = await send_referrer_warning_notification(
                referrer_data["telegram_id"],
                user_data["full_name"],
                user_data["level"],
                referrer_data["level"],
            )

            warning_results.append(
                {
                    "user": user_data,
                    "referrer": referrer_data,
                    "warning_sent": warning_sent,
                }
            )

        return {
            "success": True,
            "total_users_checked": users_needing_replacement["count"],
            "warning_results": warning_results,
        }

    except Exception as e:
        print(f"Error in bulk_check_referrer_levels: {e}")
        return {"success": False, "error": str(e)}


async def get_referrer_replacement_statistics():
    """
    Referrer almashtirish statistikasini olish
    """
    try:
        users_needing_replacement = await get_users_needing_referrer_replacement()

        if not users_needing_replacement["success"]:
            return users_needing_replacement

        stats = {
            "total_users_needing_replacement": users_needing_replacement["count"],
            "users_by_level": {},
            "referrers_by_level": {},
        }

        for user_info in users_needing_replacement["users"]:
            user_level = user_info["user"]["level"]
            referrer_level = user_info["current_referrer"]["level"]

            # Foydalanuvchilar darajasi bo'yicha
            if user_level not in stats["users_by_level"]:
                stats["users_by_level"][user_level] = 0
            stats["users_by_level"][user_level] += 1

            # Referrerlar darajasi bo'yicha
            if referrer_level not in stats["referrers_by_level"]:
                stats["referrers_by_level"][referrer_level] = 0
            stats["referrers_by_level"][referrer_level] += 1

        return {
            "success": True,
            "statistics": stats,
            "detailed_users": users_needing_replacement["users"],
        }

    except Exception as e:
        print(f"Error in get_referrer_replacement_statistics: {e}")
        return {"success": False, "error": str(e)}
