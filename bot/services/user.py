from asgiref.sync import sync_to_async
from django.db import close_old_connections
from bot.models import TelegramUser
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
    level: str,
    gender: str
) -> TelegramUser:
    """
    Creates a new Telegram user with proper async handling and connection management
    """
    try:
        # Ensure clean database connections
        await sync_to_async(close_old_connections)()
        
        # Check if user already exists
        existing_user = await sync_to_async(_get_user_sync)(telegram_id)
        if existing_user:
            logger.info(f"User {telegram_id} already exists, updating instead")
            # Update existing user
            updated = await update_user(
                telegram_id,
                phone_number=phone_number,
                full_name=full_name,
                age=age,
                telegram_username=telegram_username,
                profession=profession,
                region=region,
                level=level,
                gender=gender
            )
            if updated:
                return await sync_to_async(_get_user_sync)(telegram_id)
            else:
                logger.error(f"Failed to update existing user {telegram_id}")
                return None
        
        # Create new user with sync_to_async
        user = await sync_to_async(_create_user_sync)(
            telegram_id=telegram_id,
            phone_number=phone_number,
            full_name=full_name,
            age=age,
            telegram_username=telegram_username,
            profession=profession,
            region=region,
            level=level,
            gender=gender
        )
        
        if user:
            logger.info(f"Successfully created user {telegram_id}")
            return user
        else:
            logger.error(f"Failed to create user {telegram_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create user {telegram_id}: {str(e)}", exc_info=True)
        return None
    finally:
        await sync_to_async(close_old_connections)()

def _get_user_sync(telegram_id: str):
    """Synchronous helper function to get user"""
    try:
        return TelegramUser.objects.filter(telegram_id=telegram_id).first()
    except Exception as e:
        logger.error(f"Failed to get user {telegram_id}: {str(e)}", exc_info=True)
        return None

def _create_user_sync(**kwargs):
    """Synchronous helper function for user creation"""
    try:
        user = TelegramUser.objects.create(
            is_confirmed=False,
            **kwargs
        )
        return user
    except Exception as e:
        logger.error(f"Sync user creation failed: {str(e)}", exc_info=True)
        return None

async def update_user(chat_id: str, **kwargs) -> bool:
    """
    Updates user data with proper connection handling and validation
    """
    allowed_fields = {
        "phone_number", "full_name", 
        "telegram_username", "age", "region",
        "profession", "is_confirmed", "gender", "level"
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
        result = await sync_to_async(_update_user_sync)(chat_id, update_data)
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
        logger.info(f"Updated {updated} records for user {chat_id}")
        return updated > 0
    except Exception as e:
        logger.error(f"Sync user update failed: {str(e)}", exc_info=True)
        return False

async def get_user(telegram_id: str) -> TelegramUser:
    """
    Get user by telegram_id with proper async handling
    """
    try:
        await sync_to_async(close_old_connections)()
        user = await sync_to_async(_get_user_sync)(telegram_id)
        return user
    except Exception as e:
        logger.error(f"Failed to get user {telegram_id}: {str(e)}", exc_info=True)
        return None
    finally:
        await sync_to_async(close_old_connections)()