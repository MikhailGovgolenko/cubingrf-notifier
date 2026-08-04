from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..competitions.disciplines import DISCIPLINES


class MenuCB(CallbackData, prefix="menu"):
    """Main menu actions: settings, competitions, back."""

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


class DisciplineCB(CallbackData, prefix="disc"):
    """Discipline selection actions (toggle, select all, clear, back)."""

    action: str
    code: str = ""


def _btn(text: str, callback_data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data.pack())


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Top-level menu shown after /start."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn("📅 Соревнования", MenuCB(action="competitions")))
    kb.row(_btn("⚙️ Настройки", MenuCB(action="settings")))
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


def disciplines_keyboard(selected_codes: list[str]) -> InlineKeyboardMarkup:
    """Discipline selection menu with toggle buttons and bulk actions."""
    selected = set(selected_codes)
    kb = InlineKeyboardBuilder()

    # One toggle button per discipline; the first/last rows are kept balanced.
    buttons = [
        _btn(
            ("☑️ " if code in selected else "☐ ") + label,
            DisciplineCB(action="toggle", code=code),
        )
        for code, label in DISCIPLINES
    ]
    kb.row(*buttons[:8])
    kb.row(*buttons[8:16])
    kb.row(*buttons[16:])

    kb.row(
        _btn("✔️ Выбрать все", DisciplineCB(action="all")),
        _btn("🗑️ Сбросить", DisciplineCB(action="clear")),
    )
    kb.row(
        _btn("◀️ Назад", DisciplineCB(action="back")),
    )

    return kb.as_markup()