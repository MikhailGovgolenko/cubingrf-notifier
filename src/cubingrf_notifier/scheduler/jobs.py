from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

def create_scheduler(job_func, interval_seconds: int) -> AsyncIOScheduler:
    sched = AsyncIOScheduler()
    sched.add_job(job_func, IntervalTrigger(seconds=interval_seconds), id="check_competitions")
    return sched
