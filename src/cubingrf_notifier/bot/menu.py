from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..i18n import get_text
from .keyboards import main_menu_keyboard, MenuCB
from .user_status import show_settings_screen

router = Router()


async def _user_language(telegram_id: int) -> str:
    async with AsyncSessionLocal() as sess:
        return await UserRepository(sess).get_user_language(telegram_id)


@router.callback_query(MenuCB.filter(F.action == "back"))
async def cb_back(callback: CallbackQuery):
    language = await _user_language(callback.from_user.id)
    text = get_text(language, "menu.title")
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(language))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def cb_settings(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()