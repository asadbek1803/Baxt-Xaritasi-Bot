# tasks.py fayliga quyidagilarni qo'shing
from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from .models import TelegramUser, ReferrerUpdateQueue
from .selectors import find_suitable_referrers_for_user, replace_referrer_by_admin, compare_levels
from .services.notification import notify_referrer_warning, notify_referral_removed, notify_referrer_changed, notify_new_referral

@shared_task(bind=True)
def check_referral_levels_after_update(self, user_telegram_id):
    """
    Foydalanuvchi darajasi o'zgartirilganda referrer darajasini tekshirish
    """
    try:
        from .services.referral import handle_user_level_advancement
        result = handle_user_level_advancement(user_telegram_id)
        return {
            'status': 'success',
            'user_id': user_telegram_id,
            'result': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'user_id': user_telegram_id
        }

@shared_task(bind=True)
def process_pending_referrer_updates(self):
    """
    Barcha kutayotgan referrer yangilanishlarini qayta ishlash
    """
    from .models import ReferrerUpdateQueue
    now = timezone.now()
    
    # 24 soatdan ortiq vaqt o'tgan yangilanishlarni olish
    pending_updates = ReferrerUpdateQueue.objects.filter(
        created_at__lte=now - timedelta(hours=24),
        is_processed=False
    )
    
    results = []
    for update in pending_updates:
        try:
            # Referrer darajasini yangilaganligini tekshirish
            referrer = TelegramUser.objects.get(telegram_id=update.referrer_telegram_id)
            user = TelegramUser.objects.get(telegram_id=update.user_telegram_id)
            
            if compare_levels(referrer.level, user.level) >= 0:
                # Agar referrer darajasini oshirgan bo'lsa
                update.is_processed = True
                update.status = 'RESOLVED'
                update.save()
                results.append({
                    'user_id': update.user_telegram_id,
                    'status': 'resolved',
                    'message': 'Referrer updated their level'
                })
                continue
                
            # Admin referrerini topish (eng ko'p referralga ega admin)
            admin_referrer = TelegramUser.objects.filter(
                is_admin=True
            ).order_by('-referral_count').first()
            
            if not admin_referrer:
                continue
                
            # Referrerni almashtirish
            replace_result = replace_referrer_by_admin(
                user_telegram_id=update.user_telegram_id,
                new_referrer_telegram_id=admin_referrer.telegram_id,
                admin_telegram_id=admin_referrer.telegram_id
            )
            
            if replace_result['success']:
                # Eski referrerni xabardor qilish
                notify_referral_removed(
                    update.referrer_telegram_id,
                    user.full_name,
                    user.level
                )
                
                # Yangi referrerni xabardor qilish
                notify_new_referral(
                    admin_referrer.telegram_id,
                    user.full_name,
                    user.level
                )
                
                # Foydalanuvchini xabardor qilish
                notify_referrer_changed(
                    user.telegram_id,
                    update.referrer.full_name,
                    admin_referrer.full_name
                )
                
                update.is_processed = True
                update.status = 'AUTO_REPLACED'
                update.save()
                
                results.append({
                    'user_id': update.user_telegram_id,
                    'status': 'auto_replaced',
                    'new_referrer': admin_referrer.telegram_id
                })
                
        except Exception as e:
            results.append({
                'user_id': update.user_telegram_id,
                'status': 'error',
                'error': str(e)
            })
    
    return {
        'processed_at': now.isoformat(),
        'total_processed': len(results),
        'results': results
    }

@shared_task(bind=True)
def notify_referrer_about_level_issue(self, user_telegram_id, referrer_telegram_id):
    """
    Refererga daraja muammosi haqida ogohlantirish yuborish
    """
    try:
        user = TelegramUser.objects.get(telegram_id=user_telegram_id)
        referrer = TelegramUser.objects.get(telegram_id=referrer_telegram_id)
        
        # Ogohlantirish yuborish
        notify_referrer_warning(
            referrer_telegram_id,
            user.full_name,
            user.level,
            referrer.level
        )
        
        # Navbatga qo'shish
        ReferrerUpdateQueue.objects.create(
            user_telegram_id=user_telegram_id,
            referrer_telegram_id=referrer_telegram_id,
            user_level=user.level,
            referrer_level=referrer.level
        )
        
        return {
            'status': 'success',
            'user_id': user_telegram_id,
            'referrer_id': referrer_telegram_id
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }