from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from asgiref.sync import sync_to_async
from datetime import datetime
from core.settings import TELEGRAM_BOT_USERNAME
from .constants import (
    REGIONS,
    GENDER as GENDER_CHOICES,
    AGE_CHOICES,
    LEVEL_CHOICES, 
    STATUS_CHOICES,
    PAYMENT_TYPES
)
class TelegramUser(models.Model):
    telegram_id = models.CharField(
        max_length=50, unique=True, 
        help_text="Foydalanuvchining Telegram ID", verbose_name="Telegram ID")
    # Asosiy ma'lumotlar
    full_name = models.CharField(
                        max_length=200,
                        help_text="Foydalanuvchining To'liq Ismi",
                        verbose_name="To'liq Ism"
                                  )
    age = models.CharField(
        max_length=10, choices=AGE_CHOICES, 
        help_text="Foydalanuvchining yoshi",
        verbose_name="Yoshi"
        )

    level = models.CharField(
        max_length=20, help_text="Foydalanuvchi darajasi",
        choices=LEVEL_CHOICES, 
        verbose_name="Foydalanuvchi darajasi",
        default="0-bosqich"  # Default qiymat qo'shildi
    )

    phone_number = models.CharField(
        max_length=20, unique=True,
        help_text="Foydalanuvchining telefon raqami",
        verbose_name="Telefon raqami")
    
    telegram_username = models.CharField(
        max_length=50, blank=True, 
        null=True,
        help_text="Foydalanuvchining Telegram foydalanuvchi nomi",
        verbose_name="Telegram foydalanuvchi nomi"
        )
    # Plastik karta ma'lumotlari
    card_number = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Foydalanuvchining plastik karta raqami",
        verbose_name="Plastik karta raqami"
    )
    card_holder_full_name = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Foydalanuvchining karta egasining to'liq ismi",
        verbose_name="Karta egasining to'liq ismi"
    )

    # Joylashuv va shaxsiy ma'lumotlar
    region = models.CharField(
        max_length=50, choices=REGIONS,
        help_text="Foydalanuvchining yashash joyi",
        verbose_name="Yashash joyi"
        )
    profession = models.CharField(
        max_length=100,
        help_text="Foydalanuvchining kasbi yoki faoliyati",
        verbose_name="Kasb yoki faoliyat")
    
    # Jinsi
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES,
        help_text="Foydalanuvchining jinsi",
        verbose_name="Jins")
    
    # Ro'yxatdan o'tish vaqti
    registration_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Foydalanuvchi ro'yxatdan o'tgan sana",
        verbose_name="Ro'yxatdan o'tgan sana")
    
    # Referal tizimi
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals',
                                   help_text="Foydalanuvchini kim taklif qilgan",
                                   verbose_name="Taklif qiluvchi")
                                   
    # Referal kod (foydalanuvchini taklif qilish uchun)
    referral_code = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        help_text="Foydalanuvchining referral kodi (taklif qilish uchun)",
        verbose_name="Referral kod"
    )
    referral_count = models.PositiveIntegerField(
        default=0,
        help_text="Foydalanuvchini taklif qilganlar soni",
        verbose_name="Taklif qilganlar soni"
        )
    
    
    # Tasdiqlash tizimi
   
    is_confirmed = models.BooleanField(
        default=False,
        help_text="Foydalanuvchi tasdiqlanganmi",
        verbose_name="Tasdiqlangan")
    
   
    confirmed_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_users',
                                     help_text="Foydalanuvchini kim tasdiqlagan",
                                    verbose_name="Tasdiqlovchi")
    confirmation_date = models.DateTimeField(null=True, blank=True,
                                             help_text="Foydalanuvchi tasdiqlangan sana",
        verbose_name="Tasdiqlangan sana")
    
    # Adminlik huquqi (Bot egasi)
    is_admin = models.BooleanField(default=False, 
                                   help_text="Foydalanuvchi adminmi",
                                   verbose_name="Admin")
    
    is_blocked = models.BooleanField(default=False, verbose_name="Bloklangan")
   
    def save(self, *args, **kwargs):
        import uuid
        # Agar referral_code yo'q bo'lsa, avtomatik yaratamiz
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)
    def get_direct_referrals(self):
        """To'g'ridan-to'g'ri referallarni olish"""
        return self.referrals.filter(is_confirmed=True)
    
    def get_total_referrals_count(self):
        """Jami referallar sonini olish (barcha darajalar)"""
        # 1-daraja
        level_1 = self.referrals.count()
        
        # 2-daraja
        level_2 = TelegramUser.objects.filter(
            invited_by__invited_by=self
        ).count()
        
        # 3-daraja
        level_3 = TelegramUser.objects.filter(
            invited_by__invited_by__invited_by=self
        ).count()
        
        return level_1 + level_2 + level_3
    
    def get_referral_earnings(self):
        """Referal orqali topilgan daromad (taxminiy)"""
        # Har bir referal uchun 5000 so'm bonus
        return self.referrals.filter(is_confirmed=True).count() * 5000
    
    def get_referral_status(self):
        """Referal statusini aniqlash"""
        count = self.referrals.count()
        if count >= 50:
            return "🥇 Oltin referer"
        elif count >= 20:
            return "🥈 Kumush referer" 
        elif count >= 10:
            return "🥉 Bronza referer"
        elif count >= 5:
            return "🔰 Faol referer"
        else:
            return "👶 Yangi referer"
    
    def can_get_bonus(self):
        """Bonus olish imkoniyati borligini tekshirish"""
        # Kamida 5 ta tasdiqlangan referal kerak
        return self.referrals.filter(is_confirmed=True).count() >= 5
    
    def get_this_month_referrals(self):
        """Bu oy qo'shilgan referallar"""
        from django.utils import timezone
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.referrals.filter(
            registration_date__gte=start_of_month
        ).count()
    
    def update_referral_count(self):
        """Referal sonini yangilash"""
        self.referral_count = self.referrals.count()
        self.save(update_fields=['referral_count'])
    
    @property
    def referral_tree_depth(self):
        """Referal daraxti chuqurligi"""
        max_depth = 0
        
        def check_depth(user, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            for referral in user.referrals.all():
                check_depth(referral, current_depth + 1)
        
        check_depth(self)
        return max_depth
    
    def get_referral_conversion_rate(self):
        """Referal konversiya darajasi (tasdiqlangan/jami)"""
        total = self.referrals.count()
        if total == 0:
            return 0
        
        confirmed = self.referrals.filter(is_confirmed=True).count()
        return round((confirmed / total) * 100, 1)

    def get_referral_link(self):
        if not self.referral_code:
            self.referral_code = self.telegram_id
            self.save()
          # Bu yerga o'zingizning bot username-ini yozing
        return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={self.referral_code}"
    
    @sync_to_async
    def aget_referral_code(self):
        return self.get_referral_code()
    
    @sync_to_async 
    def aget_referral_link(self):
        return self.get_referral_link()
    
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    class Meta:
        verbose_name = "Telegram Foydalanuvchisi"
        verbose_name_plural = "Telegram Foydalanuvchilari"
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['referral_code']),
            models.Index(fields=['is_confirmed', 'registration_date']),
        ]

class ReferralPayment(models.Model):
    user = models.ForeignKey(
        TelegramUser, 
        on_delete=models.CASCADE,
        related_name='referral_payments_made',
        verbose_name="To'lovchi"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='REFERRAL',
        verbose_name="To'lov turi"
    )
    referrer = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='referral_payments_received',
        verbose_name="Referral egasi"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="To'lov miqdori"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Holati"
    )
    screenshot = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_referral_payments',
        verbose_name="Tasdiqlovchi"
    )

    def __str__(self):
        return f"{self.user.full_name} → {self.referrer.full_name} ({self.amount})"

    class Meta:
        verbose_name = "Referral to'lovi"
        verbose_name_plural = "Referral to'lovlari"


class Kurslar(models.Model):
    name = models.CharField(max_length=500, 
                            verbose_name="Kurs nomi",
                            help_text="Kurs uchun nom bering")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Kurslar narxi",
        help_text="Kurslar uchun to'lov narxi")
    description = models.TextField(
        verbose_name="Kurs uchun tavsif",
        help_text="Kurs uchun tavsif bering"
        )
    level = models.CharField(
        max_length=20, choices=LEVEL_CHOICES,
        verbose_name="Kurs darajasi",
        help_text="Kurs bosqichi (Har bir bosqichda 1 ta kurs)"
    )
    private_channel = models.URLField(
        verbose_name="Kurs uchun yopiq kanal",
        help_text= "Kurs uchun yopiq kanal  joylang"
    )
    start_date = models.DateField(
        verbose_name="Boshlanish vaqti",
        blank=True, null=True
    )
    end_date = models.DateField(
        verbose_name="Tugash vaqti",
        blank=True, null=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faoliyat holati",
        help_text="Kurs faolmi yoki yo'qmi"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana",
        help_text="Kurs qachon yaratilgan"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan sana",
        help_text="Kurs qachon yangilangan"
    )

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]




class Payments(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='payments',
                             verbose_name="Foydalanuvchi", help_text="To'lov qilgan foydalanuvchi")
    course = models.ForeignKey(Kurslar, on_delete=models.CASCADE, related_name='payments',verbose_name="Kurs", help_text="To'lov qilingan kurs", null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2,
                                 verbose_name="To'lov miqdori", help_text="To'lov miqdori")
    payment_screenshot = models.ImageField(
        upload_to='payments', null=True, blank=True, 
        verbose_name="To'lov skrinshoti",
        help_text="To'lov skrinshoti (agar mavjud bo'lsa)")
    payment_type = models.CharField(
        max_length=20, choices=PAYMENT_TYPES, default='KONKURS',
        verbose_name="To'lov turi", help_text="To'lov turi: Konkurs, Kurs yoki Xayriya"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="To'lov holati",
        help_text="To'lov holati: Kutilmoqda, Tasdiqlangan yoki Rad etilgan"
    ) 
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="To'lov sanasi",help_text="To'lov amalga oshirilgan sana")
    confirmed_by = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='confirmed_payments',
        verbose_name="Tasdiqlovchi admin",
        help_text="To'lovni kim tasdiqlagan"
    )
    confirmed_date = models.DateTimeField(
        null=True, blank=True, 
        verbose_name="Tasdiqlangan sana", 
        help_text="To'lov qachon tasdiqlangan"
    )
    rejection_reason = models.TextField(
        null=True, blank=True, 
        verbose_name="Rad etish sababi", 
        help_text="Agar to'lov rad etilgan bo'lsa, sababi"
    )
    is_confirmed = models.BooleanField(
        default=False, 
        verbose_name="Tasdiqlangan (eski)", 
        help_text="Bu maydon status maydoni bilan almashtirildi"
    )

    def save(self, *args, **kwargs):
        # Status va is_confirmed ni sinxronlash
        if self.status == 'CONFIRMED':
            self.is_confirmed = True
            if not self.confirmed_date:
                self.confirmed_date = timezone.now()
        else:
            self.is_confirmed = False
        super().save(*args, **kwargs)
    
    # Payments modeliga qo'shimcha
    def confirm_payment(self):
        self.status = 'CONFIRMED'
        self.is_confirmed = True
        self.confirmed_date = timezone.now()
        
        
        # Foydalanuvchi darajasini yangilash
        levels = list(LEVEL_CHOICES)
        # Find index by value (label), fallback to key if needed
        try:
            current_level_index = [label for key, label in levels].index(self.user.level)
        except ValueError:
            # If not found by label, try by key
            current_level_index = [key for key, label in levels].index(self.user.level)
        if current_level_index < len(levels) - 1:
            new_level = levels[current_level_index + 1][0]  # get the key for the next level
            self.user.level = new_level

        self.user.save()
        self.save()
        

        # Kurs to'lovi bo'lsa
        if self.payment_type == 'COURSE' and self.course:
            CourseParticipant.objects.get_or_create(
                user=self.user,
                course=self.course,
                payment=self
            )
            # Referal bonusini hisoblash
            if self.user.invited_by:
                referrer = self.user.invited_by
                referrer.referral_count += 1
                referrer.save()
            Notification.objects.create(
                recipient=self.user,
                sender=None,  # Admin yoki tizim xabari
                notification_type='PAYMENT_CONFIRMED',
                title="To'lov tasdiqlandi",
                message=f"Sizning to'lovingiz {self.amount} so'm miqdorida tasdiqlandi. Kursga qo'shildingiz!",
                extra_data={
                    'course_id': self.course.id if self.course else None,
                    'payment_id': self.id
                }
            )
    
    def reject_payment(self, reason):
        self.status = 'REJECTED'
        self.is_confirmed = False
        self.rejection_reason = reason
        self.save()
        
        Notification.objects.create(
            recipient=self.user,
            sender=None,  # Admin yoki tizim xabari
            notification_type='PAYMENT_REJECTED',
            title="To'lov rad etildi",
            message=f"Sizning to'lovingiz {self.amount} so'm miqdorida rad etildi. Sababi: {reason}",
            extra_data={
                'payment_id': self.id
            }
        )
    def clean(self):
        """
        Model validatsiyasi
        """
        if self.status == 'CONFIRMED' and not self.confirmed_by:
            from django.core.exceptions import ValidationError
            raise ValidationError("Tasdiqlangan to'lov uchun admin ko'rsatilishi kerak")
    
   
        
    
    def __str__(self):
        if self.course:
            return f"{self.user.full_name} - {self.course.name} ({self.amount}) [{self.get_status_display()}]"
        return f"{self.user.full_name} - {self.amount} [{self.get_status_display()}]"
    
    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['status', 'payment_date']),
            models.Index(fields=['user', 'course']),
        ]



class CourseParticipant(models.Model):
    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE,
        related_name='course_participants_users',
        verbose_name="Foydalanuvchi",
        help_text="Kurs ishtirokchisi foydalanuvchisi")
    course = models.ForeignKey(
        Kurslar, on_delete=models.CASCADE,
        related_name='course_participants',
        verbose_name="Kurs",
        help_text="Kurs ishtirokchisi kursi")
    payment = models.OneToOneField(
        Payments, on_delete=models.CASCADE,
        related_name='course_participant_payments',
        verbose_name="To'lov",
        help_text="Kurs ishtirokchisi to'lovi")
    joined_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan sana",
        help_text="Kurs ishtirokchisi qo'shilgan sana")
    private_channel_invited = models.BooleanField(
        default=False,
        verbose_name="Yopiq kanalga taklif qilingan",
        help_text="Kurs ishtirokchisi yopiq kanalga taklif qilinganmi")

    
    def __str__(self):
        return f"{self.user.full_name} - {self.course.name}"
    
    class Meta:
        unique_together = ('user', 'course')
        verbose_name = "Kurs ishtirokchisi"
        verbose_name_plural = "Kurs ishtirokchilari"


class MandatoryChannel(models.Model):
    name = models.CharField(max_length=255, verbose_name="Kanal nomi")
    telegram_id = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name="Telegram ID",
        help_text="Chat ID yoki @username")
    link = models.URLField(
        null=True, blank=True,
        verbose_name="Kanal havola",
        help_text="Kanalga kirish havola")
    is_telegram = models.BooleanField(
        default=True,
        verbose_name="Telegram kanali",
        help_text="Bu Telegram kanali yoki boshqa platforma")
    is_private = models.BooleanField(
        default=False,
        verbose_name="Yopiq kanal",
        help_text="Bu yopiq kanal (invite link orqali)")
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol",
        help_text="Kanal faolmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    def __str__(self):
        return f"{self.name} ({'Faol' if self.is_active else 'Nofaol'})"
    
    class Meta:
        verbose_name = "Majburiy kanal"
        verbose_name_plural = "Majburiy kanallar"
        ordering = ['name']


class PrivateChannel(models.Model):
    kurslar = models.ForeignKey(
        Kurslar, on_delete=models.CASCADE, 
        related_name='private_channels',
        verbose_name="kurslar",
        help_text="Bu yopiq kanal qaysi konkurs uchun")
    name = models.CharField(max_length=255, verbose_name="Kanal nomi")
    telegram_id = models.CharField(
        max_length=100, 
        verbose_name="Telegram ID",
        help_text="Kanalning Chat ID")
    invite_link = models.URLField(
        verbose_name="Taklif havola",
        help_text="Kanalga taklif qilish uchun havola")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    
    def __str__(self):
        return f"{self.name} ({self.konkurs.title})"
    
    class Meta:
        verbose_name = "Yopiq kanal"
        verbose_name_plural = "Yopiq kanallar"
        ordering = ['name', ]



class Notification(models.Model):
    """Bildirishnomalar tizimi"""
    NOTIFICATION_TYPES = [
        ('PAYMENT_PENDING', 'To\'lov kutilmoqda'),
        ('PAYMENT_CONFIRMED', 'To\'lov tasdiqlandi'),
        ('PAYMENT_REJECTED', 'To\'lov rad etildi'),
        ('KONKURS_JOINED', 'Konkursga qo\'shildi'),
        ('CHANNEL_INVITATION', 'Kanalga taklif'),
        ('SYSTEM_MESSAGE', 'Tizim xabari'),
    ]
    
    recipient = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Qabul qiluvchi",
        help_text="Bildirishni qabul qiluvchi foydalanuvchi")
    sender = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='sent_notifications',
        verbose_name="Jo'natuvchi",
        help_text="Bildirishni jo'natgan foydalanuvchi (admin)")
    notification_type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        verbose_name="Bildirish turi")
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="O'qilgan sana")
    
    # Qo'shimcha ma'lumotlar (JSON formatida)
    extra_data = models.JSONField(
        null=True, blank=True,
        verbose_name="Qo'shimcha ma'lumot",
        help_text="Bildirish bilan bog'liq qo'shimcha ma'lumotlar")
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def __str__(self):
        status = "O'qilgan" if self.is_read else "O'qilmagan"
        return f"{self.recipient.full_name} - {self.title} ({status})"
    
    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
        ]


class Gifts(models.Model):
    name = models.CharField(max_length=255, verbose_name="Sovg'a nomi")
    description = models.TextField(verbose_name="Sovg'alar haqida ma'lumotnoma")
    image = models.ImageField(
        upload_to='gifts', null=True, blank=True,
        verbose_name="Sovg'a rasmi",
        help_text="Sovg'a uchun rasm (agar mavjud bo'lsa)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Yaratilgan sana",
        help_text="Sovg'a qachon yaratilgan"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Faoliyat holati",
        help_text="Sovg'a faolmi yoki yo'qmi"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Yangilangan sana",
        help_text="Sovg'a qachon yangilangan"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sovg'a"
        verbose_name_plural = "Sovg'alar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
