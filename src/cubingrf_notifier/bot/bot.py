from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent, Message
from aiogram.filters import Command

from ..config import settings
from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from .menu import router as menu_router, MAIN_MENU_TEXT
from .settings import router as settings_router
from .notifications import router as notifications_router
from .competitions import router as competitions_router
from .disciplines import router as disciplines_router
from .keyboards import main_menu_keyboard

import logging

logger = logging.getLogger(__name__)


bot = Bot(token=settings.telegram_token) if settings.telegram_token else None

dp = Dispatcher()
dp.include_router(menu_router)
dp.include_router(settings_router)
dp.include_router(notifications_router)
dp.include_router(disciplines_router)
dp.include_router(competitions_router)


@dp.errors()
async def errors_handler(event: ErrorEvent):
    """Log every unhandled exception with its full traceback."""
    logger.error("Unhandled error while processing update", exc_info=event.exception)
    return True


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Register/enable the user and open the main menu."""
    user = message.from_user
    if user is None:
        return

    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        existing = await user_repo.get_user_by_telegram_id(user.id)
        if existing is None:
            await user_repo.create_user(user.id)
        else:
            await user_repo.set_notifications_enabled(user.id, True)
        await sess.commit()

    await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Помощь\n\n"
        "Управляйте ботом через кнопки главного меню.\n\n"
        "/start — открыть главное меню\n"
        "/competitions — ближайшие соревнования\n"
        "/help — список команд"
    )
