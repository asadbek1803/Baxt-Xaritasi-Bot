import os
from django.urls import reverse_lazy
from pathlib import Path
from celery import Celery
from dotenv import load_dotenv
from celery.schedules import crontab


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-2)h%6&fi_(_3*uzd^gkep9)7ywo%c3y+cr-k2*g3dv=b0y@e#l",
)
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]  # Allow all hosts for development; change in production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "telegram_notifications.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "myapp.signals": {  # O'z app nomingizni yozing
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}


CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = False  # Better to explicitly whitelist
CORS_REPLACE_HTTPS_REFERER = True

# Update these lists
CORS_ORIGIN_WHITELIST = [
    "https://newlive.uz",
    "http://newlive.uz",
    "https://27a34e8e96dd.ngrok-free.app",
    "https://d74fed7cf4a7.ngrok-free.app",
    "https://0aaca1b5a486.ngrok-free.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CSRF_TRUSTED_ORIGINS = [
    "https://newlive.uz",
    "http://newlive.uz",
    "https://27a34e8e96dd.ngrok-free.app",
    "https://d74fed7cf4a7.ngrok-free.app",
    "https://0aaca1b5a486.ngrok-free.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Set CSRF cookie domain (use None for local development)
CSRF_COOKIE_DOMAIN = None  # Or ".ngrok-free.app" if using ngrok in production
CSRF_COOKIE_SECURE = True  # For HTTPS
CSRF_COOKIE_HTTPONLY = False  # JavaScript needs to access it
CSRF_COOKIE_SAMESITE = "Lax"  # Or 'None' if needed for cross-site
# Celery sozlamalari

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Tashkent"
celery_app = Celery("core")
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"

celery_app.conf.broker_url = "redis://redis:6379/0"
celery_app.conf.result_backend = "redis://redis:6379/1"

CELERY_BEAT_SCHEDULE = {
    "update_loosers_referalls_to_admin": {
        "task": "bot.tasks.update_loosers_referalls_to_admin",
        "schedule": crontab(minute=0),  # Har soat
    },
    "check_active_users": {
        "task": "bot.tasks.check_active_users",
        "schedule": crontab(day_of_week="sunday", hour=0, minute=0),
    },
    "deactivate_inactive_users": {
        "task": "bot.tasks.deactivate_inactive_users",
        "schedule": crontab(hour=2, minute=0),  # Har kuni soat 2:00 da
    },
}

# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.import_export",
    "unfold.contrib.simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bot",
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Directory for custom templates
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Keyinchalik
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",  # SQLite ma'lumotlar bazasi
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [os.path.join(BASE_DIR, "staticfiles")]
MEDIA_URL = "/media/"  # Should be single /media/
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # Points to your media folder
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Admin CSS qo'shish uchun
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# File upload sozlamalari
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Ruxsat berilgan fayl turlari
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


UNFOLD = {
    "SITE_TITLE": "Baxt Xaritasi Bot",
    "SITE_HEADER": "Baxt Xaritasi Bot Admin",
    "SITE_SUBHEADER": "Admin panel",
    "SITE_URL": "/",
    "SITE_SYMBOL": "favorite",  # symbol from icon set
    "SHOW_HISTORY": True,  # show/hide "History" button, default: True
    "SHOW_VIEW_ON_SITE": True,  # show/hide "View on site" button, default: True
    "SHOW_BACK_BUTTON": False,
    "THEME": "light",  # Force theme: "dark" or "light". Will disable theme switcher
    "BORDER_RADIUS": "6px",
    "COLORS": {
        "primary": {
            "50": "240 248 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Menu",
                "collapsable": True,
                "items": [
                    {
                        "title": ("Dashboard"),
                        "link": reverse_lazy("admin:index"),
                        "icon": "dashboard",
                    },
                    {
                        "title": ("Foydalanuvchilar"),
                        "link": reverse_lazy("admin:bot_telegramuser_changelist"),
                        "icon": "account_circle",
                    },
                    {
                        "title": ("Majburiy kanallar"),
                        "link": reverse_lazy("admin:bot_mandatorychannel_changelist"),
                        "icon": "link",
                    },
                    {
                        "title": ("Bildirishnomalar"),
                        "link": reverse_lazy("admin:bot_notification_changelist"),
                        "icon": "notifications",
                    },
                    {
                        "title": ("To'lovlar"),
                        "link": reverse_lazy("admin:bot_payments_changelist"),
                        "icon": "payment",
                    },
                    {
                        "title": ("Referral To'lovlar"),
                        "link": reverse_lazy("admin:bot_referralpayment_changelist"),
                        "icon": "payment",
                    },
                    {
                        "title": ("Kurs qatnashchilari"),
                        "link": reverse_lazy("admin:bot_courseparticipant_changelist"),
                        "icon": "group_add",
                    },
                    {
                        "title": ("Kurslar"),
                        "link": reverse_lazy("admin:bot_kurslar_changelist"),
                        "icon": "book",
                    },
                    {
                        "title": ("Sovg'alar"),
                        "link": reverse_lazy("admin:bot_gifts_changelist"),
                        "icon": "card_giftcard",
                    },
                    {
                        "title": ("Referali yangilanadigan foydalanuvchilar"),
                        "link": reverse_lazy(
                            "admin:bot_looseruser_changelist"
                        ),
                        "icon": "account_circle",
                    },
                ],
            }
        ],
    },
}
