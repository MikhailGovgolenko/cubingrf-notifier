from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .keyboards import SettingsCB, settings_keyboard
from .user_status import settings_screen_text, show_settings_screen
from .notifications import show_notifications_screen

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    text = await settings_screen_text(message.from_user.id)
    await message.answer(text, reply_markup=settings_keyboard())


@router.callback_query(SettingsCB.filter(F.action == "notifications"))
async def cb_settings_notifications(callback: CallbackQuery):
    await show_notifications_screen(callback)
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "region"))
async def cb_region(callback: CallbackQuery):
    await callback.answer("Этот раздел появится в следующих версиях.", show_alert=True)


@router.callback_query(SettingsCB.filter(F.action == "back"))
async def cb_settings_back(callback: CallbackQuery):
    await show_settings_screen(callback)
    await callback.answer()