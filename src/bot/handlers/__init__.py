from aiogram import Router

from src.bot.handlers.account import router as account_router
from src.bot.handlers.emoji_status import router as emoji_status_router
from src.bot.handlers.start import router as start_router

router = Router()

router.include_router(start_router)
router.include_router(emoji_status_router)
router.include_router(account_router)
