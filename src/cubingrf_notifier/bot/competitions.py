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
from ..competitions.disciplines import discipline_label
from ..i18n import get_text
from .keyboards import competitions_keyboard, MenuCB, CompetitionCB

logger = logging.getLogger(__name__)

router = Router()

PAGE_SIZE = 10

_RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

_EN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

_REG_LABEL_KEYS = {
    "open": "competitions.reg_open",
    "scheduled": "competitions.reg_scheduled",
    "closed": "competitions.reg_closed",
}


def _format_date(d: datetime, language: str = "ru") -> str:
    if d is None:
        return get_text(language, "unknown_date")
    months = _RU_MONTHS if language == "ru" else _EN_MONTHS
    return f"{d.day} {months[d.month]} {d.year}"


def _format_competition(c: Competition, language: str = "ru") -> str:
    """Single competition card: name, date, location, disciplines, registration, link."""
    lines = [
        f"🏆 {c.name}",
        "",
        get_text(language, "competitions.date", date=_format_date(c.date, language)),
        get_text(language, "competitions.location", location=c.location or "-"),
    ]

    discipline_codes = c.disciplines or []
    if discipline_codes:
        labels = ", ".join(discipline_label(code) for code in discipline_codes)
        lines.append(f"\n{get_text(language, 'competitions.disciplines')}\n{labels}")

    reg_key = _REG_LABEL_KEYS.get(c.reg_status or "")
    if reg_key:
        lines.append(f"\n{get_text(language, reg_key)}")

    if c.url:
        lines.append(f"\n🔗 {c.url}")

    return "\n".join(lines)


def _format_competitions(
    comps: List[Competition],
    language: str = "ru",
) -> str:
    if not comps:
        return get_text(language, "competitions.title") + "\n\n" + get_text(language, "competitions.none")

    blocks = [get_text(language, "competitions.title")]
    blocks.extend(_format_competition(c, language) for c in comps)
    return "\n\n---\n\n".join(blocks)


async def _load_page(page: int, telegram_id: int) -> Tuple[List[Competition], int, str]:
    async with AsyncSessionLocal() as sess:
        repo = CompetitionRepository(sess)
        comps = await repo.list_upcoming_competitions()
        selected = await UserRepository(sess).get_user_disciplines(telegram_id)
        language = await UserRepository(sess).get_user_language(telegram_id)

    if selected:
        chosen = set(selected)
        before = len(comps)
        comps = [c for c in comps if chosen & set(c.disciplines or [])]
        logger.info(
            "Discipline filter (telegram_id=%s): %s selected, %s/%s matched",
            telegram_id, sorted(chosen), len(comps), before,
        )

    total = len(comps)
    start = page * PAGE_SIZE
    comps = comps[start:start + PAGE_SIZE]
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    return comps, total_pages, language


def _render(
    comps: List[Competition],
    page: int,
    total_pages: int,
    language: str,
) -> Tuple[str, object]:
    return (
        _format_competitions(comps, language),
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
        comps, total_pages, language = await _load_page(page, telegram_id)
        logger.info("Found competitions count=%s", len(comps))
        text, kb = _render(comps, page, total_pages, language)
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
    comps, total_pages, language = await _load_page(0, message.from_user.id)
    text, kb = _render(comps, 0, total_pages, language)
    await message.answer(text, reply_markup=kb)