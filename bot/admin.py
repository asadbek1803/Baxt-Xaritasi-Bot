from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils import timezone
from .models import (
    TelegramUser,
    Payments,
    MandatoryChannel,
    PrivateChannel,
    Notification,
    Kurslar,
    CourseParticipant,
    Gifts,
    ReferrerUpdateQueue,
    ReferralPayment,
)


from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.conf import settings
import os


@admin.register(ReferralPayment)
class ReferralPaymentAdmin(ModelAdmin):
    list_display = (
        "get_user_info",
        "get_referrer_info", 
        "get_payment_type_info",
        "amount",
        "get_status_badge",
        "get_screenshot_thumbnail",
        "created_at_short",
        "get_admin_actions",
    )
    
    search_fields = (
        "user__full_name",
        "user__phone_number", 
        "user__telegram_id",
        "referrer__full_name",
        "referrer__phone_number",
        "referrer__telegram_id",
    )
    
    list_filter = (
        "status",
        "payment_type", 
        "created_at",
        "confirmed_at",
    )
    
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    
    # Fieldsets - Batafsil ko'rish uchun
    fieldsets = (
        (
            "To'lov Ma'lumotlari", 
            {"fields": ("user", "referrer", "payment_type", "amount", "status")}
        ),
        (
            "Screenshot",
            {
                "fields": ("screenshot", "get_full_screenshot"),
            },
        ),
        (
            "Vaqt Ma'lumotlari",
            {
                "fields": ("created_at", "confirmed_at"),
            },
        ),
        (
            "Tasdiqlash Ma'lumotlari", 
            {"fields": ("confirmed_by",), "classes": ("collapse",)}
        ),
    )
    
    readonly_fields = ("created_at", "get_full_screenshot")
    
    # Custom methods
    def get_user_info(self, obj):
        return format_html(
            "<strong>{}</strong><br/>"
            "<small>📱 {}</small><br/>"
            "<small>🆔 {}</small>",
            obj.user.full_name,
            obj.user.phone_number or "—",
            obj.user.telegram_id,
        )
    get_user_info.short_description = "To'lovchi"
    
    def get_referrer_info(self, obj):
        return format_html(
            "<strong>{}</strong><br/>"
            "<small>📱 {}</small><br/>"
            "<small>🆔 {}</small>",
            obj.referrer.full_name,
            obj.referrer.phone_number or "—", 
            obj.referrer.telegram_id,
        )
    get_referrer_info.short_description = "Referrer"
    
    def get_payment_type_info(self, obj):
        type_icons = {
            "REFERRAL": "🎁",
            "BONUS": "💰", 
            "REWARD": "🏆"
        }
        icon = type_icons.get(obj.payment_type, "💳")
        return format_html(
            "<strong>{} {}</strong>",
            icon,
            obj.get_payment_type_display()
        )
    get_payment_type_info.short_description = "To'lov turi"
    
    def get_status_badge(self, obj):
        colors = {
            "PENDING": "#ffc107", 
            "CONFIRMED": "#28a745", 
            "REJECTED": "#dc3545",
            "CANCELLED": "#6c757d"
        }
        icons = {
            "PENDING": "⏳", 
            "CONFIRMED": "✅", 
            "REJECTED": "❌",
            "CANCELLED": "🚫"
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 15px; font-weight: bold; display: inline-block;">'
            "{} {}</span>",
            colors.get(obj.status, "#6c757d"),
            icons.get(obj.status, ""),
            obj.get_status_display(),
        )
    get_status_badge.short_description = "Status"
    
    def get_screenshot_thumbnail(self, obj):
        if not obj.screenshot:
            return format_html('<span style="color: #888;">📷 Yo\'q</span>')
        
        # Agar screenshot string va Telegram file ID bo'lsa
        if isinstance(obj.screenshot, str) and obj.screenshot.startswith('AgAC'):
            return format_html(
                "<span style='color: #007bff; font-weight: bold;'>📷 Telegram file</span><br>"
                "<small style='color: #6c757d;'>Admin panelda ko'rsatib bo'lmaydi</small>"
            )
        
        # Agar screenshot fayl bo'lsa
        if hasattr(obj.screenshot, 'url'):
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 80px; max-height: 80px; border-radius: 8px; border: 2px solid #ddd;" />'
                "</a>",
                obj.screenshot.url,
                obj.screenshot.url,
            )
        
        # Agar screenshot string va local fayl yo'li bo'lsa
        if isinstance(obj.screenshot, str):
            file_path = os.path.join(settings.MEDIA_ROOT, obj.screenshot)
            if os.path.exists(file_path):
                url = f"{settings.MEDIA_URL}{obj.screenshot}"
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width: 80px; max-height: 80px; border-radius: 8px; border: 2px solid #ddd;" />'
                    "</a>",
                    url, url
                )
        
        return format_html('<span style="color: #888;">📷 Xato</span>')
    
    get_screenshot_thumbnail.short_description = "Screenshot"
    
    def get_full_screenshot(self, obj):
        """To'liq o'lchamdagi screenshot ko'rish uchun"""
        if not obj.screenshot:
            return format_html(
                "<div style='text-align: center; color: #6c757d; padding: 20px;'>"
                "Screenshot yuklanmagan"
                "</div>"
            )
        
        # Agar screenshot string va Telegram file ID bo'lsa  
        if isinstance(obj.screenshot, str) and obj.screenshot.startswith('AgAC'):
            return format_html(
                "<div style='text-align: center; padding: 20px; color: #007bff;'>"
                "📷 Telegram fayl ID: <code style='word-break: break-all;'>{}</code><br>"
                "<small style='color: #dc3545;'>Admin panelda ko'rsatib bo'lmaydi</small>"
                "</div>",
                obj.screenshot
            )
        
        # Agar screenshot fayl bo'lsa
        if hasattr(obj.screenshot, 'url'):
            return format_html(
                '<div style="text-align: center;">'
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 100%; max-height: 400px; border-radius: 8px; border: 1px solid #ddd;"/></a>'
                "<p style='color: #6c757d;'>Kattaroq ko'rish uchun rasmga bosing</p>"
                "</div>",
                obj.screenshot.url, obj.screenshot.url
            )
        
        # Agar screenshot string va local fayl yo'li bo'lsa
        if isinstance(obj.screenshot, str):
            file_path = os.path.join(settings.MEDIA_ROOT, obj.screenshot)
            if os.path.exists(file_path):
                url = f"{settings.MEDIA_URL}{obj.screenshot}"
                return format_html(
                    '<div style="text-align: center;">'
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width: 100%; max-height: 400px; border-radius: 8px; border: 1px solid #ddd;"/></a>'
                    "<p style='color: #6c757d;'>Kattaroq ko'rish uchun rasmga bosing</p>"
                    "</div>",
                    url, url
                )
        
        return format_html(
            "<div style='text-align: center; color: #dc3545; padding: 20px;'>"
            "Screenshot ma'lumotlarida xatolik"
            "</div>"
        )
    
    get_full_screenshot.short_description = "To'liq Screenshot"
    
    def created_at_short(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")
    created_at_short.short_description = "Yaratilgan"
    
    def get_admin_actions(self, obj):
        """Status ko'rsatish (tasdiqlash/rad etish tugmalari yo'q)"""
        if obj.status == "CONFIRMED":
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✅ Tasdiqlangan</span><br/>'
                "<small>{}</small>",
                (
                    obj.confirmed_at.strftime("%d.%m.%Y %H:%M") 
                    if obj.confirmed_at else ""
                ),
            )
        elif obj.status == "REJECTED":
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">❌ Rad etilgan</span>'
            )
        elif obj.status == "CANCELLED":
            return format_html(
                '<span style="color: #6c757d; font-weight: bold;">🚫 Bekor qilingan</span>'
            )
        else:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">⏳ Kutilmoqda</span>'
            )
    
    get_admin_actions.short_description = "Holati"
    
    # Optimize queries
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "referrer", "confirmed_by")
    


# PrivateChannel Inline - Konkurs ichida qo'shish uchun
class PrivateChannelInline(TabularInline):
    model = PrivateChannel
    extra = 1  # Yangi konkurs yaratganda 1 ta bo'sh form
    fields = ("name", "telegram_id", "invite_link", "is_active")
    verbose_name = "Yopiq Kanal"
    verbose_name_plural = "Yopiq Kanallar"

    def has_add_permission(self, request, obj):
        return request.user.is_superuser or request.user.has_perm(
            "bot.add_privatechannel"
        )

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.has_perm(
            "bot.change_privatechannel"
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.has_perm(
            "bot.delete_privatechannel"
        )


# KonkursPayment Inline - Konkursga bog'liq to'lovlarni ko'rish uchun
class PaymentsInline(TabularInline):
    model = Payments
    extra = 0
    max_num = 0  # Yangi qo'shish imkoniyatini olib tashlash
    readonly_fields = (
        "user",
        "amount",
        "payment_date",
        "get_payment_screenshot_thumbnail",
        "status",
    )
    fields = (
        "user",
        "amount",
        "status",
        "get_payment_screenshot_thumbnail",
        "payment_date",
    )

    def get_payment_screenshot_thumbnail(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px; border-radius: 5px;" />',
                obj.payment_screenshot.url,
            )
        return "Skrinshot yo'q"

    get_payment_screenshot_thumbnail.short_description = "Skrinshot"

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    verbose_name = "Konkurs to'lovi"
    verbose_name_plural = "Konkurs to'lovlari"


class CourseParticipantInline(TabularInline):
    model = CourseParticipant
    extra = 0
    readonly_fields = ("user", "payment", "joined_date", "private_channel_invited")
    fields = ("user", "payment", "joined_date", "private_channel_invited")

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    verbose_name = "Ishtirokchi"
    verbose_name_plural = "Kurs ishtirokchilari"


class CoursePaymentsInline(TabularInline):
    model = Payments
    extra = 0
    max_num = 0
    readonly_fields = (
        "user",
        "amount",
        "payment_date",
        "get_payment_screenshot_thumbnail",
        "status",
    )
    fields = (
        "user",
        "amount",
        "status",
        "get_payment_screenshot_thumbnail",
        "payment_date",
    )

    def get_queryset(self, request):
        # Faqat kursga tegishli to'lovlarni ko'rsatish
        qs = super().get_queryset(request)
        return qs.filter(payment_type="COURSE")

    def get_payment_screenshot_thumbnail(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px; border-radius: 5px;" />',
                obj.payment_screenshot.url,
            )
        return "Skrinshot yo'q"

    get_payment_screenshot_thumbnail.short_description = "Skrinshot"

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    verbose_name = "Kurs to'lovi"
    verbose_name_plural = "Kurs to'lovlari"


@admin.register(Payments)
class PaymentsAdmin(ModelAdmin):
    list_display = (
        "get_user_info",
        "get_payment_type_info",
        "amount",
        "get_status_badge",
        "get_screenshot_thumbnail",
        "payment_date",
        "get_admin_actions",
    )

    search_fields = (
        "user__full_name",
        "course__name",
        "user__phone_number",
        "user__telegram_id",
    )

    list_filter = (
        "status",
        "payment_type",
        "payment_date",
        "confirmed_date",
        "course",
        "course__is_active",
    )

    ordering = ("-payment_date",)
    date_hierarchy = "payment_date"

    # Fieldsets - Batafsil ko'rish uchun
    fieldsets = (
        (
            "To'lov Ma'lumotlari",
            {"fields": ("user", "payment_type", "course", "amount", "status")},
        ),
        (
            "Skrinshot",
            {
                "fields": ("payment_screenshot", "get_full_screenshot"),
            },
        ),
        (
            "Vaqt Ma'lumotlari",
            {
                "fields": ("payment_date", "confirmed_date"),
            },
        ),
        (
            "Tasdiqlash Ma'lumotlari",
            {"fields": ("confirmed_by", "rejection_reason"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("payment_date", "get_full_screenshot")

    # Custom methods
    def get_user_info(self, obj):
        return format_html(
            "<strong>{}</strong><br/>"
            "<small>📱 {}</small><br/>"
            "<small>🆔 {}</small>",
            obj.user.full_name,
            obj.user.phone_number,
            obj.user.telegram_id,
        )

    get_user_info.short_description = "Foydalanuvchi"

    def get_payment_type_info(self, obj):
        if obj.payment_type == "COURSE" and obj.course:
            return format_html(
                "<strong>📚 {}:</strong><br/>"
                "<small>{}</small><br/>"
                "<small>💰 {} so'm</small>",
                obj.get_payment_type_display(),
                obj.course.name[:30] + ("..." if len(obj.course.name) > 30 else ""),
                obj.course.price,
            )
        return obj.get_payment_type_display()

    get_payment_type_info.short_description = "To'lov turi"

    def get_status_badge(self, obj):
        colors = {"PENDING": "#ffc107", "CONFIRMED": "#28a745", "REJECTED": "#dc3545"}
        icons = {"PENDING": "⏳", "CONFIRMED": "✅", "REJECTED": "❌"}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 15px; font-weight: bold; display: inline-block;">'
            "{} {}</span>",
            colors.get(obj.status, "#6c757d"),
            icons.get(obj.status, ""),
            obj.get_status_display(),
        )

    get_status_badge.short_description = "Status"

    def get_screenshot_thumbnail(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 80px; max-height: 80px; border-radius: 8px; border: 2px solid #ddd;" />'
                "</a>",
                obj.payment_screenshot.url,
                obj.payment_screenshot.url,
            )
        return format_html('<span style="color: #888;">📷 Yo\'q</span>')

    get_screenshot_thumbnail.short_description = "Skrinshot"

    def get_full_screenshot(self, obj):
        """To'liq o'lchamdagi skrinshot ko'rish uchun"""
        if obj.payment_screenshot:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 500px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />'
                "</a><br/><br/>"
                '<a href="{}" target="_blank" style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px;">'
                "🔍 To'liq o'lchamda ochish"
                "</a>",
                obj.payment_screenshot.url,
                obj.payment_screenshot.url,
                obj.payment_screenshot.url,
            )
        return "Skrinshot yuklanmagan"

    get_full_screenshot.short_description = "To'liq Skrinshot"

    def get_admin_actions(self, obj):
        """Tezkor amallar tugmalari"""
        if obj.status == "PENDING":
            return format_html(
                '<div style="display: flex; gap: 5px;">'
                '<a href="{}?action=confirm&ids={}" onclick="return confirm(\'Rostdan ham tasdiqlamoqchimisiz?\')" '
                'style="background: #28a745; color: white; padding: 4px 8px; text-decoration: none; border-radius: 3px; font-size: 12px;">'
                "✅ Tasdiqlash</a>"
                '<a href="{}?action=reject&ids={}" onclick="return confirm(\'Rostdan ham rad etmoqchimisiz?\')" '
                'style="background: #dc3545; color: white; padding: 4px 8px; text-decoration: none; border-radius: 3px; font-size: 12px;">'
                "❌ Rad etish</a>"
                "</div>",
                reverse("admin:bot_payments_changelist"),
                obj.id,
                reverse("admin:bot_payments_changelist"),
                obj.id,
            )
        elif obj.status == "CONFIRMED":
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✅ Tasdiqlangan</span><br/>'
                "<small>{}</small>",
                (
                    obj.confirmed_date.strftime("%d.%m.%Y %H:%M")
                    if obj.confirmed_date
                    else ""
                ),
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">❌ Rad etilgan</span><br/>'
                "<small>{}</small>",
                (
                    obj.rejection_reason[:50] + "..."
                    if obj.rejection_reason and len(obj.rejection_reason) > 50
                    else obj.rejection_reason or ""
                ),
            )

    get_admin_actions.short_description = "Amallar"

    # Actions
    actions = [
        "confirm_selected_payments",
        "reject_selected_payments",
        "mark_as_pending",
    ]

    def confirm_selected_payments(self, request, queryset):
        """Tanlangan to'lovlarni tasdiqlash"""
        pending_payments = queryset.filter(status="PENDING")
        count = 0

        for payment in pending_payments:
            payment.confirm_payment()  # Bu endi modeldagi metodni chaqiradi
            count += 1

        self.message_user(request, f"{count} ta to'lov tasdiqlandi.", messages.SUCCESS)

    confirm_selected_payments.short_description = "✅ Tanlangan to'lovlarni tasdiqlash"

    def reject_selected_payments(self, request, queryset):
        """Tanlangan to'lovlarni rad etish"""
        pending_payments = queryset.filter(status="PENDING")
        count = pending_payments.update(
            status="REJECTED",
            confirmed_date=timezone.now(),
            rejection_reason="Admin tomonidan rad etildi",
        )

        self.message_user(request, f"{count} ta to'lov rad etildi.", messages.WARNING)

    reject_selected_payments.short_description = "❌ Tanlangan to'lovlarni rad etish"

    def mark_as_pending(self, request, queryset):
        """Qayta ko'rib chiqish uchun PENDING qilish"""
        count = queryset.update(
            status="PENDING",
            confirmed_date=None,
            confirmed_by=None,
            rejection_reason="",
        )

        self.message_user(
            request, f"{count} ta to'lov kutish holatiga o'tkazildi.", messages.INFO
        )

    mark_as_pending.short_description = "⏳ Kutish holatiga o'tkazish"

    # URL lar orqali tezkor amallar (GET parametrlari orqali)
    def changelist_view(self, request, extra_context=None):
        if "action" in request.GET:
            action = request.GET["action"]
            ids = request.GET.get("ids", "").split(",")

            if action == "confirm" and ids:
                try:
                    payment = Payments.objects.get(id=ids[0])
                    if payment.status == "PENDING":
                        payment.confirm_payment()  # Modeldagi metodni ishlatamiz

                        self.message_user(
                            request,
                            f"To'lov (ID: {payment.id}) tasdiqlandi!",
                            messages.SUCCESS,
                        )
                except Payments.DoesNotExist:
                    self.message_user(request, "To'lov topilmadi!", messages.ERROR)

            elif action == "reject" and ids:
                try:
                    payment = Payments.objects.get(id=ids[0])
                    if payment.status == "PENDING":
                        payment.status = "REJECTED"
                        payment.confirmed_date = timezone.now()
                        payment.rejection_reason = "Admin tomonidan rad etildi"
                        payment.save()

                        self.message_user(
                            request,
                            f"To'lov (ID: {payment.id}) rad etildi!",
                            messages.WARNING,
                        )
                except Payments.DoesNotExist:
                    self.message_user(request, "To'lov topilmadi!", messages.ERROR)

        return super().changelist_view(request, extra_context)


@admin.register(Kurslar)
class KurslarAdmin(ModelAdmin):
    inlines = [CoursePaymentsInline, CourseParticipantInline]
    list_display = ("name", "level", "price", "is_active", "created_at", "referral_payment_amount")
    search_fields = ("name", "description")
    list_filter = ("is_active", "level", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        ("Yashirin kanallar", {"fields": ("private_channel",)}),
        ("Asosiy Ma'lumotlar", {"fields": ("name", "level", "description", "price", "referral_payment_amount")}),
        ("Vaqt Sozlamalari", {"fields": ("start_date", "end_date", "is_active")}),
    )

    readonly_fields = ("created_at",)


@admin.register(CourseParticipant)
class CourseParticipantAdmin(ModelAdmin):
    list_display = ("user", "course", "joined_date", "get_payment_status")
    search_fields = ("user__full_name", "course__name")
    list_filter = ("course", "joined_date", "payment__status")
    ordering = ("-joined_date",)

    def get_payment_status(self, obj):
        return obj.payment.get_status_display()

    get_payment_status.short_description = "To'lov holati"


# PRIVATECHANNEL ALOHIDA ADMIN (agar kerak bo'lsa)
@admin.register(PrivateChannel)
class PrivateChannelAdmin(ModelAdmin):
    list_display = ("name", "kurslar", "telegram_id", "is_active", "created_at")
    search_fields = ("name", "telegram_id")
    list_filter = ("is_active", "kurslar", "created_at")
    ordering = ("-created_at",)

    # Konkurs bo'yicha filter


# MANDATORYCHANNEL ADMIN
@admin.register(MandatoryChannel)
class MandatoryChannelAdmin(ModelAdmin):
    list_display = ("name", "telegram_id", "is_telegram", "is_private", "is_active")
    search_fields = ("name", "telegram_id")
    list_filter = ("is_telegram", "is_private", "is_active", "created_at")
    ordering = ("name",)


# TELEGRAMUSER ADMIN
@admin.register(TelegramUser)
class TelegramUserAdmin(ModelAdmin):
    list_display = (
        "full_name",
        "telegram_username",
        "phone_number",
        "region",
        "age",
        "is_confirmed",
        "is_admin",
        "referral_count",
        "registration_date",
        "inactive_time",
        "is_looser"
    )
    search_fields = ("full_name", "telegram_username", "phone_number", "telegram_id")
    list_filter = (
        "is_confirmed",
        "is_admin",
        "is_blocked",
        "gender",
        "region",
        "registration_date",
    )
    ordering = ("-registration_date",)
    date_hierarchy = "registration_date"

    # Fieldsets
    fieldsets = (
        ("Darajasi", {"fields": ("level",)}),
        (
            "Telegram Ma'lumotlari",
            {"fields": ("telegram_id", "telegram_username", "full_name")},
        ),
        ("Aloqa Ma'lumotlari", {"fields": ("phone_number", "region", "profession")}),
        (
            "Shaxsiy Ma'lumotlar",
            {
                "fields": (
                    "gender",
                    "age",
                    "card_number"
                )
            },
        ),
        (
            "Referral Tizimi",
            {
                "fields": ("invited_by", "referral_code", "referral_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Tasdiqlash",
            {"fields": ("is_confirmed", "confirmed_by", "confirmation_date")},
        ),
        ("Huquqlar", {"fields": ("is_admin", "is_blocked", "is_looser")}),
        ("Faoliyat", {"fields": ("registration_date",), "classes": ("collapse",)}),
    )

    readonly_fields = (
        "registration_date",
        "referral_count",
        "age",
    )


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("title", "recipient", "notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__full_name")
    list_filter = ("is_read", "notification_type", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Asosiy Ma'lumotlar",
            {
                "fields": (
                    "recipient",
                    "sender",
                    "notification_type",
                    "title",
                    "message",
                )
            },
        ),
        ("Holat", {"fields": ("is_read", "read_at")}),
        ("Vaqt", {"fields": ("created_at",)}),
        ("Qo'shimcha", {"fields": ("extra_data",), "classes": ("collapse",)}),
    )

    readonly_fields = ("created_at", "read_at")


@admin.register(Gifts)
class GiftsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        if Gifts.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    list_display = ("name", "description", "created_at", "updated_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(ReferrerUpdateQueue)
class ReferrerUpdateQueueAdmin(ModelAdmin):
    list_display = ("get_user_name", "get_referrer_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__full_name", "referrer__full_name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "-"

    get_user_name.short_description = "User"

    def get_referrer_name(self, obj):
        return obj.referrer.full_name if obj.referrer else "-"

    get_referrer_name.short_description = "Referrer"

    fieldsets = (
        ("Asosiy Ma'lumotlar", {"fields": ("status",)}),
        ("Vaqt", {"fields": ("created_at",)}),
    )


# Admin panelni sozlash
admin.site.site_header = "Konkurs Bot Boshqaruvi"
admin.site.site_title = "Konkurs Bot Admin"
admin.site.index_title = "Boshqaruv Paneli"
