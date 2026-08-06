"""Reminder that a competition's registration opens in some time.

Each user picks their own lead time (see ``User.reg_reminder_interval``), so a
reminder fires for a user only inside their chosen window before registration
opens. The decision helper (``should_send_registration_reminder``) is pure and
unit-testable; ``check_registration_reminders`` sends the due reminders using
the same matcher and notifier as regular notifications, so recipients follow
their notification/region/event settings and language.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from ..database.repository import (
    CompetitionRepository,
    UserRepository,
    NotificationRepository,
    KIND_REG_SOON,
)
from ..database.session import AsyncSessionLocal
from ..notifications.reminder_intervals import DEFAULT_REMINDER_INTERVAL
from .matcher import should_notify_user, KIND_REG_SOON as MATCH_KIND_REG_SOON
from .telegram import TelegramNotifier

from aiogram.exceptions import TelegramForbiddenError

logger = logging.getLogger(__name__)

REMINDER_WINDOW = timedelta(minutes=30)


def should_send_registration_reminder(
    registration_start_at: datetime | None,
    now: datetime | None = None,
    window: timedelta = REMINDER_WINDOW,
) -> bool:
    """True when the registration reminder should fire.

    True only while ``0 < registration_start_at - now <= window``: never after
    the moment passed, never without a known opening time, and never more than
    ``window`` in advance. Naive datetimes are treated as UTC.
    """
    if registration_start_at is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if registration_start_at.tzinfo is None:
        registration_start_at = registration_start_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    remaining = registration_start_at.astimezone(timezone.utc) - now.astimezone(timezone.utc)
    return timedelta(0) < remaining <= window


async def check_registration_reminders() -> None:
    """Send reminders for competitions opening within each user's window.

    The deduplication happens in the notifications table: the
    (user, competition, kind='reg_soon') unique constraint means a reminder is
    delivered at most once per user and competition, no matter how many
    scheduler runs happen inside the window.
    """
    async with AsyncSessionLocal() as sess:
        comp_repo = CompetitionRepository(sess)
        candidates = await comp_repo.list_competitions_with_registration_start()
        if not candidates:
            return

        user_repo = UserRepository(sess)
        users = await user_repo.list_enabled_users()
        if not users:
            return

        user_regions: Dict[int, List[str]] = {
            u.telegram_id: await user_repo.get_user_regions(u.telegram_id)
            for u in users
        }
        user_events: Dict[int, List[str]] = {
            u.telegram_id: await user_repo.get_user_events(u.telegram_id)
            for u in users
        }

        notifier = TelegramNotifier()
        notif_repo = NotificationRepository(sess)
        now = datetime.now(timezone.utc)
        sent = 0
        try:
            for comp in candidates:
                for user in users:
                    interval = user.reg_reminder_interval or DEFAULT_REMINDER_INTERVAL
                    window = timedelta(minutes=interval)
                    if not should_send_registration_reminder(comp.registration_start_at, now, window):
                        continue
                    try:
                        if not should_notify_user(
                            user,
                            comp,
                            kind=MATCH_KIND_REG_SOON,
                            user_region_keys=user_regions[user.telegram_id],
                            user_event_codes=user_events[user.telegram_id],
                        ):
                            continue
                        if await notif_repo.was_sent(user.id, comp.id, KIND_REG_SOON):
                            continue
                        await notifier.send_competition(
                            user.telegram_id,
                            comp,
                            language=user.language or "ru",
                            kind=KIND_REG_SOON,
                        )
                        await notif_repo.mark_sent(user.id, comp.id, KIND_REG_SOON)
                        sent += 1
                        logger.info(
                            "Registration reminder sent competition=%s user=%s",
                            comp.id,
                            user.telegram_id,
                        )
                    except TelegramForbiddenError:
                        logger.warning(
                            "User cannot be reached (blocked bot), marking as blocked telegram_id=%s",
                            user.telegram_id,
                        )
                        await user_repo.set_blocked(user.telegram_id)
                    except Exception:
                        logger.exception(
                            "Failed to send registration reminder competition=%s telegram_id=%s",
                            comp.id,
                            user.telegram_id,
                        )
        finally:
            await sess.commit()
            await notifier.close()
        if sent:
            logger.info("Registration reminders sent: %d", sent)