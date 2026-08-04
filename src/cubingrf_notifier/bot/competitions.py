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


async def _load_page(page: int, telegram_id: int) -> Tuple[List[Competition], int]:
    async with AsyncSessionLocal() as sess:
        comps = await CompetitionRepository(sess).list_upcoming_competitions()
        selected = await UserRepository(sess).get_user_disciplines(telegram_id)

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
    user_id = callback.from_user.id
    logger.info("Competitions button pressed (telegram_id=%s)", user_id)
    await _render_callback(callback, 0, user_id)


@router.callback_query(CompetitionCB.filter(F.action == "page"))
async def cb_competitions_page(callback: CallbackQuery, callback_data: CompetitionCB):
    await _render_callback(callback, callback_data.page, callback.from_user.id)


async def _render_callback(callback: CallbackQuery, page: int, telegram_id: int) -> None:
    """Load a competitions page, render it and update the message.

    Any error is logged with a full traceback (never silently ignored) and
    surfaced to the user via an alert.
    """
    try:
        logger.info("Loading competitions page=%s", page)
        comps, total_pages = await _load_page(page, telegram_id)
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
    comps, total_pages = await _load_page(0, message.from_user.id)
    text, kb = _render(comps, 0, total_pages)
    await message.answer(text, reply_markup=kb)
