import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import get_text
from .keyboards import SettingsCB
from .notify_settings import show_notifications_screen
from .user_status import show_settings_screen, send_settings_screen

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await send_settings_screen(message)


@router.callback_query(SettingsCB.filter(F.action == "notifications"))
async def cb_settings_notifications(callback: CallbackQuery):
    """Open the notification-settings submenu."""
    logger.info("Notification settings opened (telegram_id=%s)", callback.from_user.id)
    await show_notifications_screen(callback)
