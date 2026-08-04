import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from .keyboards import settings_main_keyboard, notifications_keyboard

logger = logging.getLogger(__name__)

router = Router()


def _notifications_text(enabled: bool) -> str:
    status = "включены ✅" if enabled else "выключены ❌"
    return f"🔔 Уведомления\n\nСтатус: {status}"


async def _load_enabled(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as sess:
        user = await UserRepository(sess).get_user_by_telegram_id(telegram_id)
    return user.notifications_enabled if user is not None else True


async def _set_enabled(telegram_id: int, enabled: bool) -> None:
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        if await repo.get_user_by_telegram_id(telegram_id) is None:
            await repo.create_user(telegram_id)
        await repo.set_notifications_enabled(telegram_id, enabled)
        await sess.commit()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer("⚙️ Настройки", reply_markup=settings_main_keyboard())


@router.callback_query(F.data == "settings:main")
async def cb_settings_main(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Настройки", reply_markup=settings_main_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({"settings:region", "settings:disciplines"}))
async def cb_coming_soon(callback: CallbackQuery):
    await callback.answer("Этот раздел появится в следующих версиях.", show_alert=True)


@router.callback_query(F.data == "settings:notifications")
async def cb_show_notifications(callback: CallbackQuery):
    enabled = await _load_enabled(callback.from_user.id)
    await callback.message.edit_text(
        _notifications_text(enabled),
        reply_markup=notifications_keyboard(enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:notif_toggle")
async def cb_toggle_notifications(callback: CallbackQuery):
    user_id = callback.from_user.id
    enabled = await _load_enabled(user_id)
    new_enabled = not enabled
    await _set_enabled(user_id, new_enabled)
    logger.info("User %s toggled notifications -> %s", user_id, new_enabled)
    await callback.message.edit_text(
        _notifications_text(new_enabled),
        reply_markup=notifications_keyboard(new_enabled),
    )
    await callback.answer()
