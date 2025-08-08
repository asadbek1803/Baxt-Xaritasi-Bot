from asgiref.sync import sync_to_async
from django.db import close_old_connections
from .models import TelegramUser
import logging

logger = logging.getLogger(__name__)

async def create_user(
    telegram_id: str,
    phone_number: str,
    full_name: str,
    age: str,
    telegram_username: str,
    profession: str,
    region: str,
    gender: str
) -> TelegramUser:
    """
    Creates a new Telegram user with proper async handling and connection management
    """
    try:
        # Ensure clean database connections
        await sync_to_async(close_old_connections)()
        
        # Create user with sync_to_async
        user = await sync_to_async(_create_user_sync)(
            telegram_id=telegram_id,
            phone_number=phone_number,
            full_name=full_name,
            age = age,
            telegram_username=telegram_username,
            profession=profession,
            region=region,
            gender=gender
        )
        return user
    except Exception as e:
        logger.error(f"Failed to create user {telegram_id}: {str(e)}", exc_info=True)
        return None
    finally:
        await sync_to_async(close_old_connections)()

def _create_user_sync(**kwargs):
    """Synchronous helper function for user creation"""
    try:
        return TelegramUser.objects.create(
            is_confirmed=False,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Sync user creation failed: {str(e)}", exc_info=True)
        raise

async def update_user(chat_id: str, **kwargs) -> bool:
    """
    Updates user data with proper connection handling and validation
    """
    allowed_fields = {
        "phone_number", "full_name", 
        "telegram_username", "age", "region",
        "profession", "is_confirmed", "gender"
    }
    
    # Filter and validate update data
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    
    if not update_data:
        logger.warning(f"No valid fields to update for user {chat_id}")
        return False

    try:
        # Ensure clean database connections
        await sync_to_async(close_old_connections)()
        
        # Perform the update
        result = await _update_user_sync(chat_id, update_data)
        return result
    except Exception as e:
        logger.error(f"Failed to update user {chat_id}: {str(e)}", exc_info=True)
        return False
    finally:
        await sync_to_async(close_old_connections)()

def _update_user_sync(chat_id: str, update_data: dict) -> bool:
    """Synchronous helper function for user updates"""
    try:
        updated = TelegramUser.objects.filter(telegram_id=chat_id).update(**update_data)
        return updated > 0
    except Exception as e:
        logger.error(f"Sync user update failed: {str(e)}", exc_info=True)
        raise