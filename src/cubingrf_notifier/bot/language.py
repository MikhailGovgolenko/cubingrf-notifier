import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import available_languages, get_text
from .keyboards import language_keyboard, SettingsCB, LanguageCB
from .user_status import show_settings_screen
from .rich import rich_html

logger = logging.getLogger(__name__)

router = Router()


async def _user_language(telegram_id: int) -> str:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_language(telegram_id)


def _language_name(code: str, language: str) -> str:
    key = "language.russian" if code == "ru" else "language.english"
    return get_text(language, key)


async def show_language_screen(callback: CallbackQuery) -> None:
    current = await _user_language(callback.from_user.id)
    text = (
        f"<h1>{get_text(current, 'language.title')}</h1><br/><br/>"
        f"{get_text(current, 'language.current', name=_language_name(current, current))}"
    )
    await callback.message.edit_text(
        rich_message=rich_html(text), reply_markup=language_keyboard(current)
    )
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "language"))
async def cb_open_language(callback: CallbackQuery):
    logger.info("Language menu opened (telegram_id=%s)", callback.from_user.id)
    await show_language_screen(callback)


@router.callback_query(LanguageCB.filter(F.action == "set"))
async def cb_set_language(callback: CallbackQuery, callback_data: LanguageCB):
    user_id = callback.from_user.id
    if callback_data.code not in available_languages():
        await callback.answer()
        return
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        if await repo.get_user_by_telegram_id(user_id) is None:
            await repo.create_user(user_id)
        await repo.set_user_language(user_id, callback_data.code)
        await sess.commit()
    logger.info("User %s language -> %s", user_id, callback_data.code)
    await show_settings_screen(callback)
    await callback.answer()


@router.callback_query(LanguageCB.filter(F.action == "back"))
async def cb_language_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()