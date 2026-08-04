import logging
import math
from datetime import datetime
from typing import List, Tuple

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database.models import Competition
from ..database.session import AsyncSessionLocal
from ..database.repository import CompetitionRepository
from .keyboards import competitions_keyboard, MenuCB, CompetitionCB

logger = logging.getLogger(__name__)

router = Router()

PAGE_SIZE = 10

_RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def _format_date(d: datetime) -> str:
    if d is None:
        return "дата неизвестна"
    return f"{d.day} {_RU_MONTHS[d.month]} {d.year}"


def _format_competitions(
    comps: List[Competition],
    page: int,
    total_pages: int
) -> str:
    if not comps:
        return "📅 Ближайших соревнований нет."

    blocks = [
        f"📅 Ближайшие соревнования\nСтраница {page + 1}/{total_pages}:"
    ]
    for c in comps:
        block = f"{c.name}\n📆 {_format_date(c.date)}\n📍 {c.location or '-'}"
        if c.url:
            block += f"\n🔗 {c.url}"
        blocks.append(block)
    return "\n\n".join(blocks)


async def _load_page(page: int) -> Tuple[List[Competition], int]:
    async with AsyncSessionLocal() as sess:
        repo = CompetitionRepository(sess)
        total = await repo.count_upcoming_competitions()
        comps = await repo.get_upcoming_competitions(offset=page * PAGE_SIZE, limit=PAGE_SIZE)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    return comps, total_pages


def _render(
    comps: List[Competition],
    page: int,
    total_pages: int
) -> Tuple[str, object]:
    return (
        _format_competitions(comps, page, total_pages),
        competitions_keyboard(page, total_pages),
    )


@router.callback_query(MenuCB.filter(F.action == "competitions"))
async def cb_menu_competitions(callback: CallbackQuery):
    logger.info("Competitions button pressed (telegram_id=%s)", callback.from_user.id)
    await _render_callback(callback, 0)


@router.callback_query(CompetitionCB.filter(F.action == "page"))
async def cb_competitions_page(callback: CallbackQuery, callback_data: CompetitionCB):
    await _render_callback(callback, callback_data.page)


async def _render_callback(callback: CallbackQuery, page: int) -> None:
    """Load a competitions page, render it and update the message.

    Any error is logged with a full traceback (never silently ignored) and
    surfaced to the user via an alert.
    """
    try:
        logger.info("Loading competitions page=%s", page)
        comps, total_pages = await _load_page(page)
        logger.info("Found competitions count=%s", len(comps))
        text, kb = _render(comps, page, total_pages)
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
    comps, total_pages = await _load_page(0)
    text, kb = _render(comps, 0, total_pages)
    await message.answer(text, reply_markup=kb)
