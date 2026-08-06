from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..competitions.disciplines import DISCIPLINES
from ..competitions.regions import ALL_REGION_KEYS
from ..i18n import get_text


class MenuCB(CallbackData, prefix="menu"):
    """Main menu actions: settings, competitions, back."""

    action: str


class SettingsCB(CallbackData, prefix="settings"):
    """Settings submenu actions."""

    action: str


class NotifCB(CallbackData, prefix="notif"):
    """Notification-settings submenu actions."""

    action: str


class ReminderCB(CallbackData, prefix="reminder"):
    """Registration-reminder interval selection actions."""

    action: str
    minutes: int = 0


class LanguageCB(CallbackData, prefix="lang"):
    """Interface language selection actions."""

    action: str
    code: str = ""


class CompetitionCB(CallbackData, prefix="comp"):
    """Competitions list actions (pagination)."""

    action: str
    page: int = 0


class EventCB(CallbackData, prefix="evt"):
    """Event selection actions (toggle, select all, clear, back)."""

    action: str
    code: str = ""


class RegionCB(CallbackData, prefix="region"):
    """Region selection actions (toggle, back)."""

    action: str
    key: str = ""


def _btn(text: str, callback_data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data.pack())


def main_menu_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Top-level menu shown after /start."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn(get_text(language, "menu.competitions"), MenuCB(action="competitions")))
    kb.row(_btn(get_text(language, "menu.settings"), MenuCB(action="settings")))
    return kb.as_markup()


def settings_keyboard(
    announcements_enabled: bool,
    registration_notifications_enabled: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Settings screen: notifications menu, region, disciplines, language."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn(get_text(language, "settings.notifications"), SettingsCB(action="notifications")))
    kb.row(_btn(get_text(language, "settings.region"), SettingsCB(action="region")))
    kb.row(_btn(get_text(language, "settings.disciplines"), SettingsCB(action="events")))
    kb.row(_btn(get_text(language, "settings.language"), SettingsCB(action="language")))
    kb.row(_btn(get_text(language, "back"), MenuCB(action="back")))
    return kb.as_markup()


def notifications_keyboard(
    announcements_enabled: bool,
    registration_notifications_enabled: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Notification-settings screen: two toggles + reminder interval."""
    kb = InlineKeyboardBuilder()
    ann_key = "settings.announcement_off" if announcements_enabled else "settings.announcement_on"
    reg_key = (
        "settings.registration_off"
        if registration_notifications_enabled
        else "settings.registration_on"
    )
    kb.row(_btn(get_text(language, ann_key), NotifCB(action="announcements")))
    kb.row(_btn(get_text(language, reg_key), NotifCB(action="registrations")))
    kb.row(_btn(get_text(language, "settings.reminder_interval"), NotifCB(action="interval")))
    kb.row(_btn(get_text(language, "back"), NotifCB(action="back")))
    return kb.as_markup()


def reminder_intervals_keyboard(current: int, language: str = "ru") -> InlineKeyboardMarkup:
    """Registration-reminder interval picker (10 min … 24 hours)."""
    from ..notifications.reminder_intervals import REMINDER_INTERVALS, reminder_interval_label

    kb = InlineKeyboardBuilder()
    for minutes in REMINDER_INTERVALS:
        mark = "✅ " if minutes == current else "⬜ "
        kb.row(
            _btn(
                mark + reminder_interval_label(minutes, language),
                ReminderCB(action="set", minutes=minutes),
            )
        )
    kb.row(_btn(get_text(language, "back"), ReminderCB(action="back")))
    return kb.as_markup()


def language_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Language selection screen."""
    kb = InlineKeyboardBuilder()
    kb.row(_btn(get_text(language, "language.russian"), LanguageCB(action="set", code="ru")))
    kb.row(_btn(get_text(language, "language.english"), LanguageCB(action="set", code="en")))
    kb.row(_btn(get_text(language, "back"), LanguageCB(action="back")))
    return kb.as_markup()


def competitions_keyboard(page: int, total_pages: int, language: str = "ru") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    # Show pagination only when there is more than one page; a single page
    # shows no "1/1" indicator at all.
    if total_pages > 1:
        row = []
        if page > 0:
            row.append(
                _btn(
                    "⬅️",
                    CompetitionCB(action="page", page=page - 1)
                )
            )

        # Non-interactive page indicator: "1/3" (leads nowhere).
        row.append(
            _btn(
                get_text(language, "competitions.page", page=page + 1, total=total_pages),
                CompetitionCB(action="none", page=page),
            )
        )

        if page < total_pages - 1:
            row.append(
                _btn(
                    "➡️",
                    CompetitionCB(action="page", page=page + 1)
                )
            )

        kb.row(*row)

    kb.row(
        _btn(
            get_text(language, "back"),
            MenuCB(action="back")
        )
    )

    return kb.as_markup()


def _picker_rows(kb: InlineKeyboardBuilder, items, selected: set[str], make_cb) -> None:
    """One row per (value, label) item, flagged checked if selected."""
    for value, label in items:
        text = ("✅ " if value in selected else "⬜ ") + label
        kb.row(_btn(text, make_cb(value)))


def events_keyboard(selected_codes: list[str], language: str = "ru") -> InlineKeyboardMarkup:
    """Event selection menu with toggle buttons and bulk actions.

    Every event is rendered on its own row (vertical list); bulk actions
    and back stay grouped at the bottom.
    """
    kb = InlineKeyboardBuilder()
    _picker_rows(kb, DISCIPLINES, set(selected_codes),
                 lambda code: EventCB(action="toggle", code=code))

    kb.row(
        _btn(get_text(language, "disciplines.all"), EventCB(action="all")),
        _btn(get_text(language, "disciplines.clear"), EventCB(action="clear")),
    )
    kb.row(
        _btn(get_text(language, "disciplines.back"), EventCB(action="back")),
    )

    return kb.as_markup()


def regions_keyboard(selected_keys: list[str], language: str = "ru") -> InlineKeyboardMarkup:
    """Region selection menu: vertical list, bulk actions and back below."""
    kb = InlineKeyboardBuilder()
    _picker_rows(kb, [(k, k) for k in ALL_REGION_KEYS], set(selected_keys),
                 lambda key: RegionCB(action="toggle", key=key))

    kb.row(
        _btn(get_text(language, "regions.all"), RegionCB(action="all")),
        _btn(get_text(language, "regions.clear"), RegionCB(action="clear")),
    )
    kb.row(
        _btn(get_text(language, "back"), RegionCB(action="back")),
    )

    return kb.as_markup()