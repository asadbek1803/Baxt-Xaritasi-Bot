from aiogram import Router
from .start import router as start_router
from .registration import router as registration_router
from .check_subscribe import router as subscription_router
from .back import router as back_router
from .my_profile import router as my_profile_router
from .buy_course import router as buy_course
from .stages import router as stages_router
from .my_team import router as my_team_router
from .referral_manajement import router as referral_management_router
from .credit_card import router as credit_card_router



router = Router()


router.include_router(start_router)
router.include_router(registration_router)
router.include_router(subscription_router)
router.include_router(back_router) 
router.include_router(buy_course)
router.include_router(my_profile_router)
router.include_router(stages_router)
router.include_router(my_team_router)
router.include_router(referral_management_router)
router.include_router(credit_card_router)


