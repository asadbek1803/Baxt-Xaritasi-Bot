from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import Payments  # Import your Payments model

@receiver(post_save, sender=Payments)
def handle_payment_confirmation(sender, instance, **kwargs):
    if instance.status == 'CONFIRMED' and not instance.is_confirmed:
        instance.confirm_payment()