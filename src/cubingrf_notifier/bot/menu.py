from aiogram import Router, F
from aiogram.types import CallbackQuery

from .keyboards import main_menu_keyboard, MenuCB
from .user_status import show_settings_screen

router = Router()

MAIN_MENU_TEXT = "🧊 CubingRF Notifier"


@router.callback_query(MenuCB.filter(F.action == "back"))
async def cb_back(callback: CallbackQuery):
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def cb_settings(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()