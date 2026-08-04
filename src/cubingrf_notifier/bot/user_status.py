import logging

from aiogram.types import CallbackQuery

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository
from ..competitions.disciplines import discipline_label
from .keyboards import settings_keyboard

logger = logging.getLogger(__name__)

NOT_SUBSCRIBED_TEXT = "Вы не подписаны на уведомления. Отправьте /start."


def format_user_status(user, discipline_codes=None) -> str:
    """Format the user's current subscription status as text.

    ``discipline_codes`` is an optional iterable of WCA codes (e.g. as stored
    in UserDiscipline). When omitted, the ``user.disciplines`` relationship is
    used instead so callers without extra queries still get correct output.
    """
    notifications = "включены ✅" if user.notifications_enabled else "выключены ❌"

    if discipline_codes is None:
        discipline_codes = [d.discipline_code for d in user.disciplines]
    labels = [discipline_label(code) for code in discipline_codes]
    disciplines = ", ".join(labels) if labels else "все"

    return (
        "📢 Текущий статус:\n\n"
        f"Уведомления: {notifications}\n\n"
        "Регион:\nВсе\n\n"
        f"Дисциплины:\n{disciplines}"
    )


async def settings_screen_text(telegram_id: int) -> str:
    """Full settings screen text (header + live user status)."""
    async with AsyncSessionLocal() as sess:
        repo = UserRepository(sess)
        user = await repo.get_user_by_telegram_id(telegram_id)
        if user is None:
            return NOT_SUBSCRIBED_TEXT
        codes = await repo.get_user_disciplines(telegram_id)
    return "⚙️ Настройки\n\n" + format_user_status(user, codes)


async def show_settings_screen(callback: CallbackQuery) -> None:
    """Render the settings screen (status + action buttons)."""
    await callback.message.edit_text(
        await settings_screen_text(callback.from_user.id),
        reply_markup=settings_keyboard(),
    )