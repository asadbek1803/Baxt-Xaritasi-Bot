from django.db import models
from .constants import REGIONS

class TelegramUser(models.Model):
    GENDER_CHOICES = [
        ('M', 'Erkak'),
        ('F', 'Ayol'),
    ]
    telegram_id = models.CharField(
        max_length=50, unique=True, 
        help_text="Foydalanuvchining Telegram ID", verbose_name="Telegram ID")
    # Asosiy ma'lumotlar
    first_name = models.CharField(
                        max_length=50,
                        help_text="Foydalanuvchining ismi",
                        verbose_name="Ism"
                                  )
    last_name = models.CharField(
        max_length=50,
        help_text="Foydalanuvchining familiyasi",
        verbose_name="Familiya"
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
    age = models.PositiveIntegerField(
        help_text="Foydalanuvchining yoshi",
        verbose_name="Yosh"
    )
    profession = models.CharField(
        max_length=100,
        help_text="Foydalanuvchining kasbi yoki faoliyati",
        verbose_name="Kasb yoki faoliyat")
    
    # Jinsi
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES
        ,help_text="Foydalanuvchining jinsi",
        verbose_name="Jins")
    
    # Ro'yxatdan o'tish vaqti
    registration_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Foydalanuvchi ro'yxatdan o'tgan sana",
        verbose_name="Ro'yxatdan o'tgan sana")
    
    # Referal tizimi
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals'
                                   , help_text="Foydalanuvchini kim taklif qilgan",
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
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"

    class Meta:
        verbose_name = "Telegram Foydalanuvchisi"
        verbose_name_plural = "Telegram Foydalanuvchilari"
        ordering = ['-registration_date']



class MandatoryChannel(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="Majburiy kanal nomi",
        verbose_name="Majburiy Kanal Nomi")
    telegram_id = models.CharField(
        max_length=100, blank=True, 
        null=True,
        help_text="Telegram kanal ID",
        verbose_name="Telegram Kanal ID")
    link = models.URLField(
        max_length=200, blank=True, 
        null=True,
        help_text="Kanalga havola",
        verbose_name="Kanalga havola"
    )
    is_telegram = models.BooleanField(
        default=True,
        help_text="Kanal Telegrammi yoki boshqa platformami",
        verbose_name="Kanal Telegrammi yoki boshqa platformami",
        blank=True,
        null=True
        )

    is_active = models.BooleanField(
        default=True,
        help_text="Kanal faolmi",
        verbose_name="Kanal faolmi"
        )
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Majburiy Kanal"
        verbose_name_plural = "Majburiy Kanallar"
        ordering = ['name']
