import logging

from aiogram.types import CallbackQuery, Message

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.disciplines import discipline_label, sort_discipline_codes, ALL_DISCIPLINE_CODES
from ..competitions.regions import sort_region_keys, ALL_REGION_KEYS, region_label
from ..i18n import DEFAULT_LANGUAGE, get_text
from ..notifications.competition_formatter import CARD_SEPARATOR
from .formatting import BULLET
from .keyboards import settings_keyboard
from .rich import rich_html

logger = logging.getLogger(__name__)


def _bullet_lines(items: list[str]) -> str:
    return "<br/>".join(f"{BULLET} {item}" for item in items)


def _regions_block(region_keys: list[str], language: str) -> str:
    if not region_keys or set(region_keys) >= set(ALL_REGION_KEYS):
        return get_text(language, "status.region_all")
    return _bullet_lines(
        [region_label(k, language) for k in sort_region_keys(region_keys)]
    )


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
    result_notifications_enabled: bool | None = None,
    event_codes=None,
    region_keys=None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """The settings screen as a Telegram Rich Message (HTML).

    Layout::

        <h1>⚙️ Settings</h1>
        <hr/>
        <h3>RSF ID</h3>
        <p>AS03</p>
        <hr/>
        <h3>🔔 Notifications</h3>
        <p>• Announcements ✅<br/>• Registrations ✅<br/>• Round results ✅</p>
        <hr/>
        <h3>🌍 Regions</h3>
        <p>• Москва</p>
        <hr/>
        <h3>🧩 Events</h3>
        <p>All events</p>
        <hr/>
        <h3>🌐 Language</h3>
        <p>🇬🇧 English</p>
    """
    if announcements_enabled is None:
        announcements_enabled = getattr(user, "announcements_enabled", True)
    if registration_notifications_enabled is None:
        registration_notifications_enabled = getattr(user, "registration_notifications_enabled", True)
    if result_notifications_enabled is None:
        result_notifications_enabled = getattr(user, "result_notifications_enabled", True)

    if event_codes is None:
        event_codes = [e.event_code for e in user.events]
    if region_keys is None:
        region_keys = [r.region_key for r in user.regions]

    rsf = getattr(user, "rsf_id", None) or get_text(language, "settings.rsf_not_set")

    sections = [
        (
            f"<h3>{get_text(language, 'settings.rsf_id')}</h3>\n"
            f"<p>{rsf}</p>"
        ),
        (
            f"<h3>{get_text(language, 'settings.notifications_section')}</h3>\n"
            f"<p>{BULLET} {get_text(language, 'settings.announcements')} {_on_off(announcements_enabled, language)}<br/>"
            f"{BULLET} {get_text(language, 'settings.registrations')} {_on_off(registration_notifications_enabled, language)}<br/>"
            f"{BULLET} {get_text(language, 'settings.results')} {_on_off(result_notifications_enabled, language)}</p>"
        ),
        f"<h3>{get_text(language, 'settings.region')}</h3>\n<p>{_regions_block(list(region_keys), language)}</p>",
        f"<h3>{get_text(language, 'settings.disciplines')}</h3>\n<p>{_events_block(list(event_codes), language)}</p>",
        f"<h3>{get_text(language, 'settings.language')}</h3>\n<p>{_language_display_name(language)}</p>",
    ]

    blocks = [f"<h1>{get_text(language, 'settings.title')}</h1>", *sections]
    return f"\n{CARD_SEPARATOR}\n".join(blocks)


async def settings_screen_text(telegram_id: int, language: str = DEFAULT_LANGUAGE) -> str:
    """Full settings screen text (header + live user status)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(telegram_id)
        if user is None:
            return f"<h1>{get_text(language, 'settings.title')}</h1>"
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
        rich_message=rich_html(text),
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
    await message.answer_rich(
        rich_html(text),
        reply_markup=settings_keyboard(
            user.announcements_enabled,
            user.registration_notifications_enabled,
            language,
        ),
    )
