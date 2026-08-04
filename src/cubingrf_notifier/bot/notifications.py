import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from .keyboards import (
    notification_toggle_keyboard,
    NotificationCB,
)
from .user_status import show_settings_screen

logger = logging.getLogger(__name__)

router = Router()


def notifications_text(enabled: bool) -> str:
    status = "включены ✅" if enabled else "выключены ❌"
    return f"🔔 Уведомления\n\nСтатус: {status}"


async def load_enabled(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as sess:
        user = await UserRepository(sess).get_user_by_telegram_id(telegram_id)
    return user.notifications_enabled if user is not None else True


async def set_enabled(telegram_id: int, enabled: bool) -> None:
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        if await repo.get_user_by_telegram_id(telegram_id) is None:
            await repo.create_user(telegram_id)
        await repo.set_notifications_enabled(telegram_id, enabled)
        await sess.commit()


async def show_notifications_screen(callback: CallbackQuery) -> None:
    """Render the notifications screen for the calling user."""
    enabled = await load_enabled(callback.from_user.id)
    await callback.message.edit_text(
        notifications_text(enabled),
        reply_markup=notification_toggle_keyboard(enabled),
    )


@router.callback_query(NotificationCB.filter(F.action == "toggle"))
async def cb_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_enabled = not await load_enabled(user_id)
    await set_enabled(user_id, new_enabled)
    logger.info("User %s toggled notifications -> %s", user_id, new_enabled)
    await show_notifications_screen(callback)
    await callback.answer()


@router.callback_query(NotificationCB.filter(F.action == "back"))
async def cb_notif_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()
