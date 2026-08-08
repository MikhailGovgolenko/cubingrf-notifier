from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
import logging
from datetime import timezone

logger = logging.getLogger(__name__)


def create_scheduler(
    job_func,
    interval_seconds: int,
    reminder_reconciler=None,
) -> AsyncIOScheduler:
    """Build the AsyncIO scheduler and register its jobs.

    ``job_func`` — the periodic check/notify job (new competitions).

    Optional ``reminder_reconciler``: a coroutine receiving the scheduler, run
    on the same periodic interval, that (re)computes the exact one-shot
    notification times for registration reminders and schedules
    ``DateTrigger`` jobs for them. That keeps the real "opening soon" delivery
    anchored to the exact ``registration_start_at - interval`` instant instead
    of a coarse periodic tick.
    """
    sched = AsyncIOScheduler(timezone=timezone.utc)
    sched.add_job(job_func, IntervalTrigger(seconds=interval_seconds), id="check_competitions")
    if reminder_reconciler is not None:
        sched.add_job(
            reminder_reconciler,
            IntervalTrigger(seconds=interval_seconds),
            id="reconcile_registration_reminders",
            replace_existing=True,
            coalesce=True,
            kwargs={"scheduler": sched},
        )
    return sched