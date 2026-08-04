from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .keyboards import settings_keyboard, SettingsCB
from .notifications import show_notifications_screen
from .disciplines import show_disciplines_screen

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer("⚙️ Настройки", reply_markup=settings_keyboard())


@router.callback_query(SettingsCB.filter(F.action == "notifications"))
async def cb_settings_notifications(callback: CallbackQuery):
    await show_notifications_screen(callback)
    await callback.answer()


@router.callback_query(SettingsCB.filter(F.action == "region"))
async def cb_region(callback: CallbackQuery):
    await callback.answer("Этот раздел появится в следующих версиях.", show_alert=True)


@router.callback_query(SettingsCB.filter(F.action == "back"))
async def cb_settings_back(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Настройки", reply_markup=settings_keyboard())
    await callback.answer()