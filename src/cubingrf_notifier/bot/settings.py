import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import get_text
from .keyboards import SettingsCB
from .user_status import show_settings_screen, send_settings_screen

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await send_settings_screen(message)


@router.callback_query(SettingsCB.filter(F.action == "notifications"))
async def cb_settings_notifications(callback: CallbackQuery):
    """Toggle notifications in one tap and return to the settings screen."""
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(user_id)
        if user is None:
            user = await repo.create_user(user_id)
        await repo.set_notifications_enabled(user_id, not user.notifications_enabled)
        await sess.commit()
    logger.info("User %s toggled notifications", user_id)
    await show_settings_screen(callback)
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "region"))
async def cb_region(callback: CallbackQuery):
    await callback.answer("Этот раздел появится в следующих версиях.", show_alert=True)