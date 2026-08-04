from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuCB(CallbackData, prefix="menu"):
    """Main menu actions: status, settings, notifications, competitions, back."""

    action: str


class SettingsCB(CallbackData, prefix="settings"):
    """Settings submenu actions."""

    action: str


class NotificationCB(CallbackData, prefix="notif"):
    """Notifications toggle actions."""

    action: str


class CompetitionCB(CallbackData, prefix="comp"):
    """Competitions list actions (pagination)."""

    action: str
    page: int = 0


def _btn(text: str, callback_data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data.pack())


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Top-level menu shown after /start."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn("📅 Соревнования", MenuCB(action="competitions")))
    kb.row(_btn("🔔 Уведомления", MenuCB(action="notifications")))
    kb.row(_btn("⚙️ Настройки", MenuCB(action="settings")))
    kb.row(_btn("ℹ️ Статус", MenuCB(action="status")))
    return kb.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    """Settings submenu with a back-to-main button."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn("🔔 Уведомления", SettingsCB(action="notifications")))
    kb.row(_btn("🌍 Регион", SettingsCB(action="region")))
    kb.row(_btn("🧩 Дисциплины", SettingsCB(action="disciplines")))
    kb.row(_btn("◀️ Назад", MenuCB(action="back")))
    return kb.as_markup()


def notification_toggle_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Notifications screen: on/off toggle plus back-to-settings button."""
    kb = InlineKeyboardBuilder()
    action = "Выключить" if enabled else "Включить"
    kb.row(_btn(action, NotificationCB(action="toggle")))
    kb.row(_btn("◀️ Назад", SettingsCB(action="back")))
    return kb.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Generic back-to-main-menu button."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn("◀️ Назад", MenuCB(action="back")))
    return kb.as_markup()


def competitions_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    row = []

    if page > 0:
        row.append(
            _btn(
                "⬅️",
                CompetitionCB(action="page", page=page - 1)
            )
        )

    if page < total_pages - 1:
        row.append(
            _btn(
                "➡️",
                CompetitionCB(action="page", page=page + 1)
            )
        )

    if row:
        kb.row(*row)

    kb.row(
        _btn(
            "◀️ Назад",
            MenuCB(action="back")
        )
    )

    return kb.as_markup()