import logging

from aiogram.types import CallbackQuery, Message

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.disciplines import discipline_label, sort_discipline_codes, ALL_DISCIPLINE_CODES
from ..competitions.regions import sort_region_keys, ALL_REGION_KEYS
from ..i18n import DEFAULT_LANGUAGE, get_text
from ..notifications.competition_formatter import CARD_SEPARATOR
from .formatting import BULLET
from .keyboards import settings_keyboard

logger = logging.getLogger(__name__)


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"{BULLET} {item}" for item in items)


def _regions_block(region_keys: list[str], language: str) -> str:
    if not region_keys or set(region_keys) >= set(ALL_REGION_KEYS):
        return get_text(language, "status.region_all")
    return _bullet_lines(sort_region_keys(region_keys))


def _events_block(event_codes: list[str], language: str) -> str:
    if not event_codes or set(event_codes) >= set(ALL_DISCIPLINE_CODES):
        return get_text(language, "settings.events_all")
    return _bullet_lines([discipline_label(c) for c in sort_discipline_codes(event_codes)])


def _language_display_name(language: str) -> str:
    key = "language.name_russian" if language == "ru" else "language.name_english"
    return get_text(language, key)


def _on_off(enabled: bool, language: str) -> str:
    return get_text(
        language,
        "status.notifications_enabled" if enabled else "status.notifications_disabled",
    )


def format_settings_rich(
    user,
    *,
    announcements_enabled: bool | None = None,
    registration_notifications_enabled: bool | None = None,
    event_codes=None,
    region_keys=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """The settings screen as a Telegram Rich Message (HTML).

    Layout::

        <b>⚙️ Settings</b>
        ──────────────────
        <b>🔔 Notifications</b>
        • Announcements ✅
        • Registrations ✅
        ──────────────────
        <b>🌍 Regions</b>
        • Москва
        ──────────────────
        <b>🧩 Events</b>
        All events
        ──────────────────
        <b>🌐 Language</b>
        🇬🇧 English
    """
    if announcements_enabled is None:
        announcements_enabled = getattr(user, "announcements_enabled", True)
    if registration_notifications_enabled is None:
        registration_notifications_enabled = getattr(user, "registration_notifications_enabled", True)

    if event_codes is None:
        event_codes = [e.event_code for e in user.events]
    if region_keys is None:
        region_keys = [r.region_key for r in user.regions]

    sections = [
        (
            f"<b>{get_text(language, 'settings.notifications_section')}</b>\n"
            f"{BULLET} {get_text(language, 'settings.announcements')} {_on_off(announcements_enabled, language)}\n"
            f"{BULLET} {get_text(language, 'settings.registrations')} {_on_off(registration_notifications_enabled, language)}"
        ),
        f"<b>{get_text(language, 'settings.region')}</b>\n{_regions_block(list(region_keys), language)}",
        f"<b>{get_text(language, 'settings.disciplines')}</b>\n{_events_block(list(event_codes), language)}",
        f"<b>{get_text(language, 'settings.language')}</b>\n{_language_display_name(language)}",
    ]

    blocks = [f"<b>{get_text(language, 'settings.title')}</b>", *sections]
    return f"\n{CARD_SEPARATOR}\n".join(blocks)


async def settings_screen_text(telegram_id: int, language: str = DEFAULT_LANGUAGE) -> str:
    """Full settings screen text (header + live user status)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(telegram_id)
        if user is None:
            return f"<b>{get_text(language, 'settings.title')}</b>"
        codes = await repo.get_user_events(telegram_id)
        regions = await repo.get_user_regions(telegram_id)
    language = user.language or language
    return format_settings_rich(user, event_codes=codes, region_keys=regions, language=language)


async def build_settings(user, codes, language: str, region_keys=None) -> str:
    """Settings text for an already loaded user."""
    return format_settings_rich(user, event_codes=codes, region_keys=region_keys, language=language)


async def show_settings_screen(callback: CallbackQuery) -> None:
    """Render the settings screen (status + action buttons)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(callback.from_user.id)
        if user is None:
            user = await repo.create_user(callback.from_user.id)
            await sess.commit()
        codes = await repo.get_user_events(callback.from_user.id)
        regions = await repo.get_user_regions(callback.from_user.id)
        language = user.language or DEFAULT_LANGUAGE
    text = await build_settings(user, codes, language, regions)
    await callback.message.edit_text(
        text,
        reply_markup=settings_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            language,
        ),
    )


async def send_settings_screen(message: Message) -> None:
    """Render the settings screen as a reply to a message (e.g. /settings)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(message.from_user.id)
        if user is None:
            user = await repo.create_user(message.from_user.id)
            await sess.commit()
        codes = await repo.get_user_events(message.from_user.id)
        regions = await repo.get_user_regions(message.from_user.id)
        language = user.language or DEFAULT_LANGUAGE
    text = await build_settings(user, codes, language, regions)
    await message.answer(
        text,
        reply_markup=settings_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            language,
        ),
    )
