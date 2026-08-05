import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.regions import REGION_LABELS
from ..i18n import get_text
from .keyboards import (
    regions_keyboard,
    SettingsCB,
    RegionCB,
)
from .user_status import show_settings_screen

logger = logging.getLogger(__name__)

router = Router()


async def _load_selected(telegram_id: int) -> list[str]:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_regions(telegram_id)


async def _user_language(telegram_id: int) -> str:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_language(telegram_id)


def _regions_text(selected: list[str], language: str = "ru") -> str:
    if not selected:
        return f"{get_text(language, 'regions.title')}\n\n{get_text(language, 'regions.none')}"
    labels = ", ".join(REGION_LABELS.get(key, key) for key in selected)
    return f"{get_text(language, 'regions.title')}\n\n{labels}"


async def show_regions_screen(callback: CallbackQuery) -> None:
    selected = await _load_selected(callback.from_user.id)
    language = await _user_language(callback.from_user.id)
    await callback.message.edit_text(
        _regions_text(selected, language),
        reply_markup=regions_keyboard(selected, language),
    )
    await callback.answer()


async def _apply(telegram_id: int, keys: list[str]) -> None:
    async with AsyncSessionLocal() as sess:
        await UserRepository(sess).set_user_regions(telegram_id, keys)
        await sess.commit()


@router.callback_query(SettingsCB.filter(F.action == "region"))
async def cb_open_regions(callback: CallbackQuery):
    logger.info("Regions menu opened (telegram_id=%s)", callback.from_user.id)
    await show_regions_screen(callback)


@router.callback_query(RegionCB.filter(F.action == "toggle"))
async def cb_region_toggle(callback: CallbackQuery, callback_data: RegionCB):
    user_id = callback.from_user.id
    current = set(await _load_selected(user_id))
    key = callback_data.key
    if key in current:
        current.discard(key)
    else:
        current.add(key)
    await _apply(user_id, sorted(current))
    logger.info("User %s region selection -> %s", user_id, sorted(current))
    await show_regions_screen(callback)


@router.callback_query(RegionCB.filter(F.action == "back"))
async def cb_regions_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()