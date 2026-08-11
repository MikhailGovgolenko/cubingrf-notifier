"""Notification-settings submenu: per-type toggles and the reminder interval."""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import get_text
from ..notifications.reminder_intervals import (
    is_valid_reminder_interval,
    reminder_interval_label,
)
from .keyboards import (
    notifications_keyboard,
    reminder_intervals_keyboard,
    NotifCB,
    ReminderCB,
)
from .user_status import show_settings_screen
from .rich import rich_html

logger = logging.getLogger(__name__)

router = Router()


class RsfEditState(StatesGroup):
    """Awaiting the user's RSF ID while editing it."""

    waiting_for_rsf = State()


async def _load(telegram_id: int) -> tuple:
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(telegram_id)
        if user is None:
            user = await repo.create_user(telegram_id)
            await sess.commit()
        language = user.language or "en"
        return user, language


def _notifications_text(user, language: str) -> str:
    on = get_text(language, "status.notifications_enabled")
    off = get_text(language, "status.notifications_disabled")
    rsf = user.rsf_id or get_text(language, "settings.rsf_not_set")
    lines = [
        f"{get_text(language, 'settings.announcements')}: {on if user.announcements_enabled else off}",
        f"{get_text(language, 'settings.registrations')}: {on if user.registration_notifications_enabled else off}",
        f"{get_text(language, 'settings.results')}: {on if user.result_notifications_enabled else off}",
        f"{get_text(language, 'settings.rsf_id')}: {rsf}",
        f"{get_text(language, 'settings.reminder_interval')}: {reminder_interval_label(user.reg_reminder_interval, language)}",
    ]
    body = "<br/>".join(lines)
    return f"<h1>{get_text(language, 'settings.notifications')}</h1>\n<p>{body}</p>"


def _reminder_text(user, language: str) -> str:
    return (
        f"<h1>{get_text(language, 'settings.reminder_interval')}</h1>\n"
        f"<p>{get_text(language, 'settings.reminder_current', value=reminder_interval_label(user.reg_reminder_interval, language))}</p>"
    )


async def show_notifications_screen(callback: CallbackQuery) -> None:
    user, language = await _load(callback.from_user.id)
    await callback.message.edit_text(
        rich_message=rich_html(_notifications_text(user, language)),
        reply_markup=notifications_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            user.result_notifications_enabled,
            language,
        ),
    )
    await callback.answer()


async def show_reminder_screen(callback: CallbackQuery) -> None:
    user, language = await _load(callback.from_user.id)
    await callback.message.edit_text(
        rich_message=rich_html(_reminder_text(user, language)),
        reply_markup=reminder_intervals_keyboard(user.reg_reminder_interval, language),
    )
    await callback.answer()


async def _reopen(callback: CallbackQuery) -> None:
    user, language = await _load(callback.from_user.id)
    await callback.message.edit_text(
        rich_message=rich_html(_notifications_text(user, language)),
        reply_markup=notifications_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            user.result_notifications_enabled,
            language,
        ),
    )
    await callback.answer()


@router.callback_query(NotifCB.filter(F.action == "announcements"))
async def cb_toggle_announcements(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(user_id)
        if user is None:
            user = await repo.create_user(user_id)
        await repo.set_announcements_enabled(user_id, not user.announcements_enabled)
        await sess.commit()
    logger.info("User %s announcements -> %s", user_id, not user.announcements_enabled)
    await _reopen(callback)


@router.callback_query(NotifCB.filter(F.action == "registrations"))
async def cb_toggle_registrations(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(user_id)
        if user is None:
            user = await repo.create_user(user_id)
        await repo.set_registration_notifications_enabled(user_id, not user.registration_notifications_enabled)
        await sess.commit()
    logger.info("User %s registration notifications -> %s", user_id, not user.registration_notifications_enabled)
    await _reopen(callback)


@router.callback_query(NotifCB.filter(F.action == "interval"))
async def cb_open_interval(callback: CallbackQuery):
    logger.info("Reminder interval menu opened (telegram_id=%s)", callback.from_user.id)
    await show_reminder_screen(callback)


@router.callback_query(NotifCB.filter(F.action == "back"))
async def cb_notifications_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()


@router.callback_query(ReminderCB.filter(F.action == "set"))
async def cb_set_interval(callback: CallbackQuery, callback_data: ReminderCB):
    user_id = callback.from_user.id
    minutes = callback_data.minutes
    if not is_valid_reminder_interval(minutes):
        await callback.answer()
        return
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        if await repo.get_user_by_telegram_id(user_id) is None:
            await repo.create_user(user_id)
        await repo.set_reg_reminder_interval(user_id, minutes)
        await sess.commit()
    logger.info("User %s reminder interval -> %s min", user_id, minutes)
    await _reopen(callback)


@router.callback_query(ReminderCB.filter(F.action == "back"))
async def cb_reminder_back(callback: CallbackQuery):
    await show_notifications_screen(callback)
    await callback.answer()


@router.callback_query(NotifCB.filter(F.action == "results"))
async def cb_toggle_results(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(user_id)
        if user is None:
            user = await repo.create_user(user_id)
        await repo.set_result_notifications_enabled(user_id, not user.result_notifications_enabled)
        await sess.commit()
    logger.info("User %s round results -> %s", user_id, not user.result_notifications_enabled)
    await _reopen(callback)


@router.callback_query(NotifCB.filter(F.action == "rsf"))
async def cb_edit_rsf(callback: CallbackQuery, state: FSMContext):
    """Ask the user to type their RSF ID."""
    _, language = await _load(callback.from_user.id)
    await state.set_state(RsfEditState.waiting_for_rsf)
    await callback.message.answer_rich(
        rich_html(
            f"<h1>{get_text(language, 'settings.rsf_prompt')}</h1>\n"
            f"<p>{get_text(language, 'settings.rsf_hint')}</p>"
        )
    )
    await callback.answer()


@router.message(RsfEditState.waiting_for_rsf)
async def msg_set_rsf(message: Message, state: FSMContext):
    """Capture the typed RSF ID and save it."""
    user_id = message.from_user.id
    raw = (message.text or "").strip()
    # Accept only letters + digits (typical RSF ids like "AS03").
    rsf = "".join(ch for ch in raw.upper() if ch.isalnum()) if raw else ""
    rsf = rsf or None
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        if await repo.get_user_by_telegram_id(user_id) is None:
            await repo.create_user(user_id)
        await repo.set_rsf_id(user_id, rsf)
        await sess.commit()
        language = await repo.get_user_language(user_id)
    await state.clear()
    logger.info("User %s RSF -> %s", user_id, rsf)
    # Re-render the notifications screen so the user sees the updated RSF id.
    # ``_notifications_text`` already renders the full screen (heading + body),
    # so it is passed through unchanged — wrapping it again would duplicate the
    # "Notifications" heading.
    user, language = await _load(user_id)
    await message.answer_rich(
        rich_html(_notifications_text(user, language)),
        reply_markup=notifications_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            user.result_notifications_enabled,
            language,
        ),
    )
