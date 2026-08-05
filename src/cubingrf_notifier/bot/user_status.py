import logging

from aiogram.types import CallbackQuery, Message

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.disciplines import discipline_label
from ..i18n import DEFAULT_LANGUAGE, get_text
from .formatting import status_section
from .keyboards import settings_keyboard

logger = logging.getLogger(__name__)


def format_user_status(
    user,
    discipline_codes=None,
    language: str = DEFAULT_LANGUAGE,
    region_keys=None,
) -> str:
    """Format the user's current subscription status as localized text.

    ``discipline_codes`` is an optional iterable of WCA codes (e.g. as stored
    in UserDiscipline). When omitted, the ``user.disciplines`` relationship is
    used instead so callers without extra queries still get correct output.
    ``region_keys`` works the same way for the ``user.regions`` relationship.

    Status layout:

        📢 Текущий статус

        🔔 Уведомления: ✅ Включены

        🌍 Регионы:
        • Москва
        • Санкт-Петербург

        🧩 Дисциплины:
        • 3x3x3
        • 4x4x4

        🌐 Язык: Русский
    """
    if user.notifications_enabled:
        notifications = get_text(language, "status.notifications_enabled")
    else:
        notifications = get_text(language, "status.notifications_disabled")

    language_name = _language_display_name(language)

    if discipline_codes is None:
        discipline_codes = [d.discipline_code for d in user.disciplines]
    labels = [discipline_label(code) for code in discipline_codes]

    if region_keys is None:
        region_keys = [r.region_key for r in user.regions]

    return (
        f"{get_text(language, 'status.header')}\n\n"
        f"{get_text(language, 'status.notifications')} {notifications}\n\n"
        f"{status_section(get_text(language, 'status.regions'), region_keys, get_text(language, 'status.region_all'))}\n\n"
        f"{status_section(get_text(language, 'status.disciplines'), labels, get_text(language, 'status.disciplines_all'))}\n\n"
        f"{get_text(language, 'status.language')} {language_name}"
    )


def _language_display_name(language: str) -> str:
    """Plain display name of the given language code in the same language."""
    key = "language.name_russian" if language == "ru" else "language.name_english"
    return get_text(language, key)


async def settings_screen_text(telegram_id: int, language: str = DEFAULT_LANGUAGE) -> str:
    """Full settings screen text (header + live user status)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(telegram_id)
        if user is None:
            return get_text(language, "settings.title")
        codes = await repo.get_user_disciplines(telegram_id)
        regions = await repo.get_user_regions(telegram_id)
    language = user.language or language
    return f"{get_text(language, 'settings.title')}\n\n{format_user_status(user, codes, language, regions)}"


async def build_settings(user, codes, language: str, region_keys=None) -> str:
    """Settings text for an already loaded user."""
    return f"{get_text(language, 'settings.title')}\n\n{format_user_status(user, codes, language, region_keys)}"


async def show_settings_screen(callback: CallbackQuery) -> None:
    """Render the settings screen (status + action buttons)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(callback.from_user.id)
        if user is None:
            user = await repo.create_user(callback.from_user.id)
            await sess.commit()
        codes = await repo.get_user_disciplines(callback.from_user.id)
        regions = await repo.get_user_regions(callback.from_user.id)
        language = user.language or DEFAULT_LANGUAGE
    text = await build_settings(user, codes, language, regions)
    await callback.message.edit_text(text, reply_markup=settings_keyboard(user.notifications_enabled, language))


async def send_settings_screen(message: Message) -> None:
    """Render the settings screen as a reply to a message (e.g. /settings)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(message.from_user.id)
        if user is None:
            user = await repo.create_user(message.from_user.id)
            await sess.commit()
        codes = await repo.get_user_disciplines(message.from_user.id)
        regions = await repo.get_user_regions(message.from_user.id)
        language = user.language or DEFAULT_LANGUAGE
    text = await build_settings(user, codes, language, regions)
    await message.answer(text, reply_markup=settings_keyboard(user.notifications_enabled, language))