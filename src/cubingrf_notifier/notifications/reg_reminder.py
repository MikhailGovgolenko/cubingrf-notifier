"""Reminder that a competition's registration opens in some time.

Each user picks their own lead time (see ``User.reg_reminder_interval``). A
reminder is delivered at the **exact** instant ``registration_start_at -
interval`` — never earlier, never on a coarse periodic tick. Delivery is
achieved by one-shot APScheduler ``DateTrigger`` jobs: the periodic reconciler
keeps them anchored to the exact target instant, while the original periodic
scheduler continues to discover new competitions.

The plan pure helper (``notification_time``) and the due predicate
(``should_send_registration_reminder``) are unit-testable; recipients still go
through the same matcher and notifier as regular notifications, so region /
discipline filters, the per-type switches, Rich Messages and language all
apply.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from apscheduler.triggers.date import DateTrigger

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


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a datetime (naive or aware) to a UTC-aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def notification_time(
    registration_start_at: datetime | None,
    interval_minutes: int,
) -> datetime | None:
    """The exact instant a reminder must fire: opening minus the lead time.

    ``None`` when opening time is unknown. Naive datetimes are treated as UTC.
    """
    start = _as_utc(registration_start_at)
    if start is None:
        return None
    return start - timedelta(minutes=interval_minutes)


def should_send_registration_reminder(
    registration_start_at: datetime | None,
    now: datetime | None = None,
    interval_minutes: int = DEFAULT_REMINDER_INTERVAL,
) -> bool:
    """True when the exact reminder moment has been reached, but registration
    has not opened yet.

    ``False`` before the target instant (never early) and after registration
    opens. Repeated firing of the *same* target is avoided by the per-target
    uniqueness in the notifications table, not by this predicate.
    """
    start = _as_utc(registration_start_at)
    target = notification_time(registration_start_at, interval_minutes)
    if start is None or target is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    now = _as_utc(now)
    if now is None:
        return False
    return target <= now < start


_REMINDER_JOB_PREFIX = "reg_soon_"


def _reminder_job_id(user_id: int, competition_id: int) -> str:
    return f"{_REMINDER_JOB_PREFIX}{user_id}_{competition_id}"


def reg_reminder_kind(target: datetime | None) -> str:
    """Dedup key for a registration reminder at a specific instant.

    The notifications table enforces one row per (user, competition, kind),
    and the same reminder instant must fire at most once. Because a user may
    legitimately receive *several* reminders for one competition at different
    lead times (e.g. "1 hour" then, after changing the interval, "30 minutes"),
    the kind must differ per target instant. Embedding the UTC epoch into
    ``kind`` reuses the existing unique constraint without a schema change and
    keeps 'new' announcements deduplicated independently.
    """
    if target is None:
        return KIND_REG_SOON
    return f"{KIND_REG_SOON}:{int(target.timestamp())}"


def _is_future_target(target: datetime | None, start: datetime | None, now: datetime) -> bool:
    """True when a reminder at ``target`` still lies ahead of ``now`` and
    registration has not opened yet. Past targets are deliberately skipped so
    an overdue reminder is never sent just because the interval changed.
    """
    if target is None or start is None:
        return False
    return start > now and target >= now


async def send_registration_reminder(
    user_id: int,
    competition_id: int,
) -> None:
    """Deliver a registration reminder for one (user, competition) pair.

    Re-checks eligibility and dedupes, so a job firing late (or the reconciler
    running concurrently) never results in a duplicate or stale message.
    """
    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        user = await user_repo.get_user_by_id(user_id)
        comp_repo = CompetitionRepository(sess)
        comp = await comp_repo.get_by_id(competition_id)
        if user is None or comp is None:
            return

        now = datetime.now(timezone.utc)
        start = _as_utc(comp.registration_start_at)
        if start is None or start <= now:
            return
        interval = user.reg_reminder_interval or DEFAULT_REMINDER_INTERVAL
        target = notification_time(start, interval)
        if target is None or target > now:
            return

        user_regions = await user_repo.get_user_regions(user.telegram_id)
        user_events = await user_repo.get_user_events(user.telegram_id)
        if not should_notify_user(
            user,
            comp,
            kind=MATCH_KIND_REG_SOON,
            user_region_keys=user_regions,
            user_event_codes=user_events,
        ):
            return

        notif_repo = NotificationRepository(sess)
        if await notif_repo.was_sent(user.id, comp.id, reg_reminder_kind(target)):
            return

        notifier = TelegramNotifier()
        try:
            await notifier.send_competition(
                user.telegram_id,
                comp,
                language=user.language or "ru",
                kind=KIND_REG_SOON,
            )
            await notif_repo.mark_sent(user.id, comp.id, reg_reminder_kind(target))
            await sess.commit()
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
            await sess.commit()
        except Exception:
            logger.exception(
                "Failed to send registration reminder competition=%s telegram_id=%s",
                comp.id,
                user.telegram_id,
            )
            await sess.rollback()
        finally:
            await notifier.close()


async def reconcile_registration_reminders(
    scheduler,
    session_factory=AsyncSessionLocal,
) -> None:
    """Compute the exact delivery instants and schedule one-shot jobs.

    Runs on the periodic scheduler as a reconciliation pass only — it never
    decides the actual send moment. For every (user, competition) that matches
    the user's region/discipline settings it ensures a single one-shot
    ``DateTrigger`` job is scheduled at exactly ``registration_start_at -
    current_interval``. One job slot per pair means the currently configured
    interval is always the one that fires:

    * a changed interval that yields a new *future* target replaces the old
      job (different target -> same slot, ``replace_existing``);
    * a changed interval whose target has already passed is **not** sent
      retroactively — the stale job is removed and nothing is scheduled;
    * a target that has already fired is in the past, so it is never re-queued;
      the per-target kind in the notifications table still guards delivery.

    Deduplication of a *specific* target stays on delivery, and repeated
    reconciliation never creates duplicates because an existing job whose
    ``next_run_time`` already equals the desired target is left untouched.
    """
    async with session_factory() as sess:
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

        now = datetime.now(timezone.utc)
        scheduled = 0
        removed = 0
        for comp in candidates:
            start = _as_utc(comp.registration_start_at)
            if start is None or start <= now:
                continue
            for user in users:
                job_id = _reminder_job_id(user.id, comp.id)
                if not should_notify_user(
                    user,
                    comp,
                    kind=MATCH_KIND_REG_SOON,
                    user_region_keys=user_regions[user.telegram_id],
                    user_event_codes=user_events[user.telegram_id],
                ):
                    # Not wanted (e.g. registration notifications disabled):
                    # cancel any future job for this pair.
                    if scheduler.get_job(job_id) is not None:
                        scheduler.remove_job(job_id)
                        removed += 1
                    continue

                interval = user.reg_reminder_interval or DEFAULT_REMINDER_INTERVAL
                target = notification_time(start, interval)

                existing = scheduler.get_job(job_id)
                if not _is_future_target(target, start, now):
                    # Past target (or registration already open): never send
                    # retroactively; drop any stale job for this pair.
                    if existing is not None:
                        scheduler.remove_job(job_id)
                        removed += 1
                    continue

                if existing is not None and existing.next_run_time is not None:
                    if _as_utc(existing.next_run_time) == _as_utc(target):
                        continue

                scheduler.add_job(
                    send_registration_reminder,
                    trigger=DateTrigger(run_date=target, timezone=timezone.utc),
                    id=job_id,
                    replace_existing=True,
                    misfire_grace_time=60,
                    kwargs={"user_id": user.id, "competition_id": comp.id},
                )
                scheduled += 1

        await sess.commit()
        if scheduled or removed:
            logger.info(
                "Registration reminder jobs scheduled=%d removed=%d",
                scheduled,
                removed,
            )