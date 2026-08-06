import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.disciplines import (
    discipline_label,
    sort_discipline_codes,
    ALL_DISCIPLINE_CODES,
)
from ..i18n import get_text
from .formatting import selection_screen_text
from .keyboards import (
    events_keyboard,
    SettingsCB,
    EventCB,
)
from .user_status import show_settings_screen
from .rich import rich_html

logger = logging.getLogger(__name__)

router = Router()


async def _load_selected(telegram_id: int) -> list[str]:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_events(telegram_id)


async def _user_language(telegram_id: int) -> str:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_language(telegram_id)


def _events_text(selected: list[str], language: str = "ru") -> str:
    return selection_screen_text(
        get_text(language, "disciplines.title"),
        get_text(language, "disciplines.none"),
        [discipline_label(code) for code in sort_discipline_codes(selected)],
    )


async def show_events_screen(callback: CallbackQuery) -> None:
    selected = await _load_selected(callback.from_user.id)
    language = await _user_language(callback.from_user.id)
    await callback.message.edit_text(
        rich_message=rich_html(_events_text(selected, language)),
        reply_markup=events_keyboard(selected, language),
    )
    await callback.answer()


async def _apply(telegram_id: int, codes: list[str]) -> None:
    async with AsyncSessionLocal() as sess:
        await UserRepository(sess).set_user_events(telegram_id, codes)
        await sess.commit()


@router.callback_query(SettingsCB.filter(F.action == "events"))
async def cb_open_events(callback: CallbackQuery):
    logger.info("Events menu opened (telegram_id=%s)", callback.from_user.id)
    await show_events_screen(callback)


@router.callback_query(EventCB.filter(F.action == "toggle"))
async def cb_toggle(callback: CallbackQuery, callback_data: EventCB):
    user_id = callback.from_user.id
    current = set(await _load_selected(user_id))
    code = callback_data.code
    if code in current:
        current.discard(code)
    else:
        current.add(code)
    await _apply(user_id, sorted(current))
    logger.info("User %s event selection -> %s", user_id, sorted(current))
    await show_events_screen(callback)


@router.callback_query(EventCB.filter(F.action == "all"))
async def cb_select_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await _apply(user_id, list(ALL_DISCIPLINE_CODES))
    logger.info("User %s selected all events", user_id)
    await show_events_screen(callback)


@router.callback_query(EventCB.filter(F.action == "clear"))
async def cb_clear(callback: CallbackQuery):
    user_id = callback.from_user.id
    await _apply(user_id, [])
    logger.info("User %s cleared event selection", user_id)
    await show_events_screen(callback)


@router.callback_query(EventCB.filter(F.action == "back"))
async def cb_events_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()