import os
import logging

from dotenv import load_dotenv
from django.db import close_old_connections
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from asgiref.sync import sync_to_async

from bot.handlers import router
from bot.middlewares.check_subscribe import ChannelMembershipMiddleware

# Initialize logging
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

dp.callback_query.middleware(ChannelMembershipMiddleware(bot=bot, skip_admins=True))
dp.message.middleware(ChannelMembershipMiddleware(bot=bot, skip_admins=True))

dp.include_router(router)


@csrf_exempt
async def telegram_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST method allowed")

    try:
        # Validate the incoming update
        update = Update.model_validate_json(request.body)

        # Process update with proper error handling
        await process_update(update)

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return HttpResponseBadRequest(f"Error processing update: {e}")


async def process_update(update: Update):
    """Process update with proper resource management"""
    try:
        # Clean Django DB connections before processing
        await sync_to_async(close_old_connections)()

        # Process the update through the dispatcher
        await dp.feed_update(bot, update=update)

    except Exception as e:
        logger.error(f"Failed to process update {update.update_id}: {e}", exc_info=True)
        raise
    finally:
        # Clean up Django DB connections after processing
        await sync_to_async(close_old_connections)()
        # Ensure bot session is properly closed if needed
        await bot.session.close()
