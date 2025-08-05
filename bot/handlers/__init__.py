from aiogram import Router

from .check_subscribe import router as subscription_router
from .start import router as start_router


router = Router()

router.include_router(subscription_router)
router.include_router(start_router)
