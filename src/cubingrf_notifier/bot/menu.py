from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from .keyboards import (
    main_menu_keyboard,
    back_keyboard,
    settings_keyboard,
    MenuCB,
)

router = Router()

MAIN_MENU_TEXT = "🧊 CubingRF Notifier"


@router.callback_query(MenuCB.filter(F.action == "back"))
async def cb_back(callback: CallbackQuery):
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "status"))
async def cb_status(callback: CallbackQuery):
    async with AsyncSessionLocal() as sess:
        user = await UserRepository(sess).get_user_by_telegram_id(callback.from_user.id)

    if user is None:
        text = "Вы не подписаны на уведомления. Отправьте /start."
    else:
        notifications = "включены ✅" if user.notifications_enabled else "выключены ❌"
        text = (
            "📢 Статус подписки\n\n"
            f"Уведомления: {notifications}\n\n"
            "Настройки:\n"
            "Регион: все\n"
            "Дисциплины: все"
        )

    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "settings"))
async def cb_settings(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ Настройки", reply_markup=settings_keyboard())
    await callback.answer()
