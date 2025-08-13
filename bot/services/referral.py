
from datetime import timedelta
from django.utils import timezone
from bot.models import TelegramUser, ReferrerUpdateQueue
from bot.selectors import find_suitable_referrers_for_user, compare_levels
from bot.tasks import notify_referrer_about_level_issue

def handle_user_level_advancement(user_telegram_id):
    """
    Foydalanuvchi darajasi oshganda referrer darajasini tekshirish
    """
    try:
        user = TelegramUser.objects.get(telegram_id=user_telegram_id)
        if not user.invited_by:
            return {
                'needs_replacement': False,
                'message': 'User has no referrer'
            }
        
        referrer = user.invited_by
        if compare_levels(user.level, referrer.level) <= 0:
            return {
                'needs_replacement': False,
                'message': 'Referrer level is sufficient'
            }
        
        # Referrerga ogohlantirish yuborish
        notify_referrer_about_level_issue.delay(
            user_telegram_id=user.telegram_id,
            referrer_telegram_id=referrer.telegram_id
        )
        
        return {
            'needs_replacement': True,
            'message': 'Referrer needs to upgrade their level',
            'user': {
                'telegram_id': user.telegram_id,
                'full_name': user.full_name,
                'level': user.level
            },
            'referrer': {
                'telegram_id': referrer.telegram_id,
                'full_name': referrer.full_name,
                'level': referrer.level
            }
        }
        
    except Exception as e:
        return {
            'needs_replacement': False,
            'error': str(e)
        }

def auto_replace_referrer(user_telegram_id):
    """
    Foydalanuvchi uchun yangi referrer avtomatik tanlash
    """
    try:
        user = TelegramUser.objects.get(telegram_id=user_telegram_id)
        
        # 1. Mos referrerlarni topish
        suitable_referrers = find_suitable_referrers_for_user(
            user_telegram_id==user_telegram_id,
            min_level=user.level
        )
        
        if not suitable_referrers:
            # 2. Agar mos referrer topilmasa, adminlardan birini tanlash
            admin_referrer = TelegramUser.objects.filter(
                is_admin=True
            ).order_by('-referral_count').first()
            
            if not admin_referrer:
                return {
                    'success': False,
                    'message': 'No suitable referrer found'
                }
            
            # Adminni referrer qilish
            user.invited_by = admin_referrer
            user.save()
            
            return {
                'success': True,
                'message': 'Replaced with admin referrer',
                'new_referrer': {
                    'telegram_id': admin_referrer.telegram_id,
                    'full_name': admin_referrer.full_name
                }
            }
        
        # 3. Eng yuqori darajali va ko'p referralga ega bo'lgan referrerni tanlash
        new_referrer = max(
            suitable_referrers,
            key=lambda x: (x['level_num'], x['referral_count'])
        )
        
        # Referrerni almashtirish
        user.invited_by = TelegramUser.objects.get(telegram_id=new_referrer['id'])
        user.save()
        
        return {
            'success': True,
            'message': 'Replaced with suitable referrer',
            'new_referrer': {
                'telegram_id': new_referrer['id'],
                'full_name': new_referrer['name']
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }