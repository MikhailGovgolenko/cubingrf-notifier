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


class LanguageCB(CallbackData, prefix="lang"):
    """Interface language selection actions."""

    action: str
    code: str = ""


class CompetitionCB(CallbackData, prefix="comp"):
    """Competitions list actions (pagination)."""

    action: str
    page: int = 0


class DisciplineCB(CallbackData, prefix="disc"):
    """Discipline selection actions (toggle, select all, clear, back)."""

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
    notifications_enabled: bool,
    language: str = "ru",
) -> InlineKeyboardMarkup:
    """Settings screen: toggle notifications, region, disciplines, language."""
    kb = InlineKeyboardBuilder()
    notif_key = "settings.notifications_off" if notifications_enabled else "settings.notifications_on"
    kb.row(_btn(get_text(language, notif_key), SettingsCB(action="notifications")))
    kb.row(_btn(get_text(language, "settings.region"), SettingsCB(action="region")))
    kb.row(_btn(get_text(language, "settings.disciplines"), SettingsCB(action="disciplines")))
    kb.row(_btn(get_text(language, "settings.language"), SettingsCB(action="language")))
    kb.row(_btn(get_text(language, "back"), MenuCB(action="back")))
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


def disciplines_keyboard(selected_codes: list[str], language: str = "ru") -> InlineKeyboardMarkup:
    """Discipline selection menu with toggle buttons and bulk actions.

    Every discipline is rendered on its own row (vertical list); bulk actions
    and back stay grouped at the bottom.
    """
    kb = InlineKeyboardBuilder()
    _picker_rows(kb, DISCIPLINES, set(selected_codes),
                 lambda code: DisciplineCB(action="toggle", code=code))

    kb.row(
        _btn(get_text(language, "disciplines.all"), DisciplineCB(action="all")),
        _btn(get_text(language, "disciplines.clear"), DisciplineCB(action="clear")),
    )
    kb.row(
        _btn(get_text(language, "disciplines.back"), DisciplineCB(action="back")),
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