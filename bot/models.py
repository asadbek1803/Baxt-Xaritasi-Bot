from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from asgiref.sync import sync_to_async
from datetime import datetime
from .constants import REGIONS

class TelegramUser(models.Model):
    AGE_CHOICES = [
        ('18-24', '18-24'),
        ('25-34', '25-34'),
        ('35-44', '35-44'),
        ('45+', '45+'),
    ]
    GENDER_CHOICES = [
        ('M', 'Erkak'),
        ('F', 'Ayol'),
    ]
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
   

    def get_referral_link(self):
        if not self.referral_code:
            import uuid
            from django.conf import settings
            self.referral_code = str(uuid.uuid4())[:8]
            self.save()
        bot_username = "testBot"
        return f"https://t.me/{bot_username}?start={self.referral_code}"
    def can_join_contest(self, contest):
        # Kurs to'lovi qilinganligini tekshirish
        if not self.has_active_course():
            return False
        # Konkursga allaqachon qo'shilganligini tekshirish
        return not self.konkurs_participants.filter(konkurs=contest).exists()
    
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



class Konkurslar(models.Model):
    title = models.CharField(max_length=255, verbose_name="Konkurs nomi")
    description = models.TextField(verbose_name="Konkurs tavsifi")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Konkurs narxi",
        help_text="Konkurs uchun to'lov narxi")
    konkurs_mandatory_channels = models.ManyToManyField(
        'MandatoryChannel', blank=True, related_name='konkurslar',
        verbose_name="Majburiy kanallar",
        help_text="Konkurs uchun majburiy kanallar")
    
    start_date = models.DateField(verbose_name="Boshlanish sanasi", help_text="Konkurs boshlanish sanasi ($MM/DD/YYYY)")
    end_date = models.DateField(verbose_name="Tugash sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Faoliyat holati")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    
    # Qo'shimcha maydonlar
    max_participants = models.PositiveIntegerField(
        null=True, blank=True, 
        verbose_name="Maksimal ishtirokchilar soni",
        help_text="Konkursga maksimal ishtirokchilar soni (bo'sh bo'lsa cheksiz)"
    )
    winner_count = models.PositiveIntegerField(
        default=1, 
        verbose_name="G'oliblar soni",
        help_text="Konkursda g'olib bo'luvchilar soni"
    )

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError('Tugash sanasi boshlanish sanasidan keyin bo\'lishi kerak.')
        if self.winner_count < 1:
            raise ValidationError('G\'oliblar soni kamida 1 ta bo\'lishi kerak.')

    def get_participants_count(self):
        return self.payments.filter(status='CONFIRMED').values('user').distinct().count()
    
    def is_full(self):
        if self.max_participants:
            return self.get_participants_count() >= self.max_participants
        return False
    
    def is_ongoing(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Konkurs"
        verbose_name_plural = "Konkurslar"
        ordering = ['-created_at']


class Payments(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('CONFIRMED', 'Tasdiqlangan'),
        ('REJECTED', 'Rad etilgan')
    ]
    PAYMENT_TYPES = [
        ('KONKURS', 'Konkurs to\'lovi'),
        ('COURSE', 'Kurs to\'lovi'),
        ('DONATION', 'Xayriya to\'lovi')
    ]
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='payments',
                             verbose_name="Foydalanuvchi", help_text="To'lov qilgan foydalanuvchi")
    course = models.ForeignKey(Kurslar, on_delete=models.CASCADE, related_name='payments',verbose_name="Kurs", help_text="To'lov qilingan kurs", null=True, blank=True)
    konkurs = models.ForeignKey(Konkurslar, on_delete=models.CASCADE, related_name='payments',verbose_name="Konkurs", help_text="To'lov qilingan konkurs", null=True, blank=True)
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
        
        # Konkurs to'lovi bo'lsa
        elif self.payment_type == 'KONKURS' and self.konkurs:
            KonkursParticipant.objects.get_or_create(
                user=self.user,
                konkurs=self.konkurs,
                payment=self
            )
    
    def __str__(self):
        if self.konkurs:
            return f"{self.user.full_name} - {self.konkurs.title} ({self.amount}) [{self.get_status_display()}]"
        elif self.course:
            return f"{self.user.full_name} - {self.course.name} ({self.amount}) [{self.get_status_display()}]"
        return f"{self.user.full_name} - {self.amount} [{self.get_status_display()}]"
    
    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['status', 'payment_date']),
            models.Index(fields=['user', 'konkurs']),
            models.Index(fields=['user', 'course']),
        ]




# class KonkursPayment(models.Model):
#     STATUS_CHOICES = [
#         ('PENDING', 'Kutilmoqda'),
#         ('CONFIRMED', 'Tasdiqlangan'),
#         ('REJECTED', 'Rad etilgan')
#     ]
    
#     user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='payments',
#     verbose_name="Foydalanuvchi", help_text="To'lov qilgan foydalanuvchi")
#     konkurs = models.ForeignKey(Konkurslar, on_delete=models.CASCADE, related_name='payments', 
#     verbose_name="Konkurs", help_text="To'lov qilingan konkurs")
#     amount = models.DecimalField(max_digits=10, decimal_places=2,
#     verbose_name="To'lov miqdori", help_text="To'lov miqdori")
#     payment_screenshot = models.ImageField(
#         upload_to='payments', null=True, blank=True, 
#         verbose_name="To'lov skrinshoti",
#         help_text="To'lov skrinshoti (agar mavjud bo'lsa)")
#     payment_date = models.DateTimeField(auto_now_add=True, verbose_name="To'lov sanasi",
#     help_text="To'lov amalga oshirilgan sana")
    
#     # Status maydonlari
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='PENDING',
#         verbose_name="To'lov holati",
#         help_text="To'lov holati: Kutilmoqda, Tasdiqlangan yoki Rad etilgan"
#     )
    
#     # Tasdiqlovchi admin va sanasi
#     confirmed_by = models.ForeignKey(
#         TelegramUser, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='confirmed_payments',
#         verbose_name="Tasdiqlovchi admin",
#         help_text="To'lovni kim tasdiqlagan"
#     )
#     confirmed_date = models.DateTimeField(
#         null=True, blank=True, 
#         verbose_name="Tasdiqlangan sana", 
#         help_text="To'lov qachon tasdiqlangan")
    
#     rejection_reason = models.TextField(
#         null=True, blank=True, 
#         verbose_name="Rad etish sababi", 
#         help_text="Agar to'lov rad etilgan bo'lsa, sababi")

#     # Deprecated field - backward compatibility uchun
#     is_confirmed = models.BooleanField(
#         default=False, 
#         verbose_name="Tasdiqlangan (eski)", 
#         help_text="Bu maydon status maydoni bilan almashtirildi")

#     def save(self, *args, **kwargs):
#         # Status va is_confirmed ni sinxronlash
#         if self.status == 'CONFIRMED':
#             self.is_confirmed = True
#             if not self.confirmed_date:
#                 self.confirmed_date = timezone.now()
#         else:
#             self.is_confirmed = False
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.user.full_name} - {self.konkurs.title} ({self.amount}) [{self.get_status_display()}]"

#     class Meta:
#         verbose_name = "Konkurs to'lovi"
#         verbose_name_plural = "Konkurs to'lovlari"
#         ordering = ['-payment_date']
#         indexes = [
#             models.Index(fields=['status', 'payment_date']),
#             models.Index(fields=['user', 'konkurs']),
#         ]

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

class KonkursParticipant(models.Model):
    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE,
        related_name='konkurs_participants_users',
        verbose_name="Foydalanuvchi",
        help_text="Konkurs ishtirokchisi foydalanuvchisi")
    konkurs = models.ForeignKey(
        Konkurslar, on_delete=models.CASCADE,
        related_name='konkurs_participants',
        verbose_name="Konkurs",
        help_text="Konkurs ishtirokchisi konkursi")
    payment = models.OneToOneField(
        Payments, on_delete=models.CASCADE,
        related_name='konkurs_participant_payments',
        verbose_name="To'lov",
        help_text="Konkurs ishtirokchisi to'lovi")
    joined_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan sana",
        help_text="Konkurs ishtirokchisi qo'shilgan sana")
    private_channel_invited = models.BooleanField(
        default=False,
        verbose_name="Yopiq kanalga taklif qilingan",
        help_text="Konkurs ishtirokchisi yopiq kanalga taklif qilinganmi")
    referral_link = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="Referal havola",
        help_text="Konkurs ishtirokchisi uchun referal havola"
        )
    
    def save(self, *args, **kwargs):
        # Referal link yaratish
        if not self.referral_link:
            self.referral_link = self.user.get_referral_link()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.full_name} - {self.konkurs.title}"
    
    class Meta:
        unique_together = ('user', 'konkurs')
        verbose_name = "Konkurs ishtirokchisi"
        verbose_name_plural = "Konkurs ishtirokchilari"
        ordering = ['-joined_date']


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
    konkurs = models.ForeignKey(
        Konkurslar, on_delete=models.CASCADE, 
        related_name='private_channels',
        verbose_name="Konkurs",
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
        ordering = ['konkurs', 'name']



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