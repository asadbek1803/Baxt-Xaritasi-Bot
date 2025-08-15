import os
from celery import Celery

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('bot')

# Django sozlamalaridan Celery konfiguratsiyasini yuklash
app.config_from_object('django.conf:settings', namespace='CELERY')

# Barcha ilovalardagi tasks.py fayllarini avtomatik topish
app.autodiscover_tasks()
