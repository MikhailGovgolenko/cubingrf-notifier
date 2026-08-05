from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, Message
from aiogram.filters import Command

from ..config import settings
from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import get_text
from .menu import router as menu_router
from .settings import router as settings_router
from .competitions import router as competitions_router
from .events import router as events_router
from .regions import router as regions_router
from .language import router as language_router
from .keyboards import main_menu_keyboard
from .middleware import SyncUsernameMiddleware

import logging

logger = logging.getLogger(__name__)


bot = (
    Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    if settings.telegram_token
    else None
)

dp = Dispatcher()
dp.message.outer_middleware(SyncUsernameMiddleware())
dp.callback_query.outer_middleware(SyncUsernameMiddleware())
dp.include_router(menu_router)
dp.include_router(settings_router)
dp.include_router(events_router)
dp.include_router(regions_router)
dp.include_router(language_router)
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
        await user_repo.register_user(user.id, user.username, user.language_code)
        await user_repo.set_notifications_enabled(user.id, True)
        await sess.commit()
        language = await user_repo.get_user_language(user.id)

    text = get_text(language, "menu.title")
    await message.answer(text, reply_markup=main_menu_keyboard(language))


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Помощь\n\n"
        "Управляйте ботом через кнопки главного меню.\n\n"
        "/start — открыть главное меню\n"
        "/competitions — ближайшие соревнования\n"
        "/settings — настройки\n"
        "/help — список команд"
    )