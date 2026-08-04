from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Any
import asyncio
import logging

logger = logging.getLogger(__name__)

def create_scheduler(job_func, interval_seconds: int) -> AsyncIOScheduler:
    sched = AsyncIOScheduler()
    sched.add_job(job_func, IntervalTrigger(seconds=interval_seconds), id="check_competitions")
    return sched

async def run_scheduler(sched: AsyncIOScheduler):
    sched.start()
    # keep running while the event loop is running
    while True:
        await asyncio.sleep(3600)
