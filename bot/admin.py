from django.contrib import admin
from .models import TelegramUser, MandatoryChannel
from django.contrib.auth.models import User, Group

# Unregister the default User and Group models
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'region', 'age', 'is_confirmed', 'registration_date')
    search_fields = ('first_name', 'last_name', 'phone_number', 'telegram_username')
    list_filter = ('region', 'is_confirmed')
    ordering = ('-registration_date',)

@admin.register(MandatoryChannel)
class MandatoryChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'is_active')
    search_fields = ('name', 'telegram_id')
    list_filter = ('is_active',)
    ordering = ('name',)
