from django.contrib import admin
from django.urls import path
from bot.views import telegram_webhook
from core.admin import custom_admin_index

# Media and static files settings
from django.conf import settings
from django.conf.urls.static import static


admin.site.index = custom_admin_index

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", admin.site.urls),
    path("webhook/", telegram_webhook),
]
# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
