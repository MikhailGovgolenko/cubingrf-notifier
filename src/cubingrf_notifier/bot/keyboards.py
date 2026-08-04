from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def settings_main_keyboard() -> InlineKeyboardMarkup:
    """Top-level settings menu."""
    kb = InlineKeyboardBuilder()
    kb.row(_button("🔔 Уведомления", "settings:notifications"))
    kb.row(_button("🌍 Регион", "settings:region"))
    kb.row(_button("🧩 Дисциплины", "settings:disciplines"))
    return kb.as_markup()


def notifications_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Notifications submenu: toggle on/off plus a back button."""
    kb = InlineKeyboardBuilder()
    action = "Выключить" if enabled else "Включить"
    kb.row(_button(action, "settings:notif_toggle"))
    kb.row(_button("◀️ Назад", "settings:main"))
    return kb.as_markup()
