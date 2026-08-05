import logging
import math
from datetime import datetime
from typing import List, Tuple

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database.models import Competition
from ..database.session import AsyncSessionLocal
from ..database.repository import CompetitionRepository, UserRepository
from ..notifications.competition_formatter import (
    CARD_SEPARATOR,
    format_competition_card,
    format_date,
    format_date_range,
    short_location,
    disciplines_line,
)
from ..i18n import get_text
from ..competitions.regions import region_key_from_location
from .keyboards import competitions_keyboard, MenuCB, CompetitionCB

logger = logging.getLogger(__name__)

router = Router()

PAGE_SIZE = 10


def _format_date(d: datetime, language: str = "ru") -> str:
    return format_date(d, language)


def _format_date_range(
    start: datetime | None,
    end: datetime | None,
    language: str = "ru",
) -> str:
    return format_date_range(start, end, language)


def _short_location(location: str | None) -> str:
    return short_location(location)


def _disciplines_line(codes: List[str], language: str) -> str | None:
    return disciplines_line(codes, language)


def _format_competition(c: Competition, language: str = "ru") -> str:
    return format_competition_card(c, language)


def _format_competitions(
    comps: List[Competition],
    language: str = "ru",
    total_count: int | None = None,
) -> str:
    if not comps:
        return get_text(language, "competitions.title") + "\n\n" + get_text(language, "competitions.none")

    blocks = [get_text(language, "competitions.title")]
    if total_count is not None:
        blocks.append(get_text(language, "competitions.matching", count=total_count))
    blocks.extend(_format_competition(c, language) for c in comps)
    return f"\n\n{CARD_SEPARATOR}\n\n".join(blocks)


def filter_competitions(
    comps: List[Competition],
    discipline_codes: List[str] | None = None,
    region_keys: List[str] | None = None,
) -> List[Competition]:
    """Apply user filters (disciplines and/or regions) to a competition list.

    An empty selection for either dimension means "show everything" for that
    dimension, so the two dimensions compose independently.
    """
    if discipline_codes:
        chosen = set(discipline_codes)
        comps = [c for c in comps if chosen & set(c.disciplines or [])]

    if region_keys:
        chosen = set(region_keys)
        comps = [c for c in comps if region_key_from_location(c.location) in chosen]

    return comps


async def _load_page(page: int, telegram_id: int) -> Tuple[List[Competition], int, str, int]:
    async with AsyncSessionLocal() as sess:
        repo = CompetitionRepository(sess)
        comps = await repo.list_upcoming_competitions()
        selected = await UserRepository(sess).get_user_disciplines(telegram_id)
        regions = await UserRepository(sess).get_user_regions(telegram_id)
        language = await UserRepository(sess).get_user_language(telegram_id)

    before = len(comps)
    comps = filter_competitions(comps, selected, regions)
    total_count = len(comps)
    if total_count != before:
        logger.info(
            "Filters (telegram_id=%s): disciplines=%s regions=%s, %s/%s matched",
            telegram_id, sorted(selected), sorted(regions), total_count, before,
        )

    start = page * PAGE_SIZE
    comps = comps[start:start + PAGE_SIZE]
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    return comps, total_pages, language, total_count


def _render(
    comps: List[Competition],
    page: int,
    total_pages: int,
    language: str,
    total_count: int,
) -> Tuple[str, object]:
    return (
        _format_competitions(comps, language, total_count),
        competitions_keyboard(page, total_pages, language),
    )


@router.callback_query(MenuCB.filter(F.action == "competitions"))
async def cb_menu_competitions(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info("Competitions button pressed (telegram_id=%s)", user_id)
    await _render_callback(callback, 0, user_id)


@router.callback_query(CompetitionCB.filter(F.action == "page"))
async def cb_competitions_page(callback: CallbackQuery, callback_data: CompetitionCB):
    await _render_callback(callback, callback_data.page, callback.from_user.id)


@router.callback_query(CompetitionCB.filter(F.action == "none"))
async def cb_competitions_none(callback: CallbackQuery):
    """Page indicator tap: no-op, just acknowledge the callback."""
    await callback.answer()


async def _render_callback(callback: CallbackQuery, page: int, telegram_id: int) -> None:
    """Load a competitions page, render it and update the message.

    Any error is logged with a full traceback (never silently ignored) and
    surfaced to the user via an alert.
    """
    try:
        logger.info("Loading competitions page=%s", page)
        comps, total_pages, language, total_count = await _load_page(page, telegram_id)
        logger.info("Found competitions count=%s", len(comps))
        text, kb = _render(comps, page, total_pages, language, total_count)
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        logger.exception(
            "Error while rendering competitions (telegram_id=%s)",
            callback.from_user.id,
        )
        await callback.answer("Не удалось загрузить соревнования", show_alert=True)
        return
    await callback.answer()


@router.message(Command("competitions"))
async def cmd_competitions(message: Message):
    comps, total_pages, language, total_count = await _load_page(0, message.from_user.id)
    text, kb = _render(comps, 0, total_pages, language, total_count)
    await message.answer(text, reply_markup=kb)
