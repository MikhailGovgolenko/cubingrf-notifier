"""Reconciliation semantics for registration reminders.

These tests exercise ``reconcile_registration_reminders`` against an in-memory
DB and a fake APScheduler, driving the "change the interval -> re-plan the
one-shot DateTrigger" behaviour requested for reg_soon reminders.
"""
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from cubingrf_notifier.database.models import Base, User, Competition
from cubingrf_notifier.database.repository import NotificationRepository, UserRepository
from cubingrf_notifier.notifications.reg_reminder import (
    reconcile_registration_reminders,
    _reminder_job_id,
    reg_reminder_kind,
    notification_time,
)


def _utc(*args, **kwargs):
    return datetime(*args, tzinfo=timezone.utc, **kwargs)


# A 2030 start is comfortably in the future relative to the real clock, so
# every target stays future and the tests are deterministic.
START = _utc(2030, 1, 1, 13, 0)


class _Job:
    def __init__(self, job_id, next_run_time):
        self.id = job_id
        self.next_run_time = next_run_time


class _FakeScheduler:
    """Minimal APScheduler stand-in recording scheduled one-shot jobs."""

    def __init__(self):
        self.jobs = {}

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def add_job(self, fn, *, trigger, id, replace_existing=False, misfire_grace_time=0, kwargs=None):
        self.jobs[id] = _Job(id, trigger.run_date)

    def remove_job(self, job_id):
        self.jobs.pop(job_id, None)


@pytest.fixture
async def factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def make_user(user_kwargs=None, comp_kwargs=None):
        async with session_factory() as sess:
            user = User(telegram_id=777, language="ru", **({"reg_reminder_interval": 60} | (user_kwargs or {})))
            comp = Competition(
                external_id="RESCH",
                name="Reschedule Open",
            )
            if comp_kwargs:
                for key, value in comp_kwargs.items():
                    setattr(comp, key, value)
            comp.registration_start_at = comp.registration_start_at or START
            sess.add_all([user, comp])
            await sess.commit()
            await sess.refresh(user)
            await sess.refresh(comp)
            return user, comp

    yield session_factory, make_user
    await engine.dispose()


def _job_next_run(sched, user_id, comp_id):
    job = sched.get_job(_reminder_job_id(user_id, comp_id))
    return job.next_run_time if job is not None else None


async def _set_interval(session_factory, user_id, minutes):
    async with session_factory() as sess:
        await UserRepository(sess).set_reg_reminder_interval(user_id, minutes)
        await sess.commit()


async def _set_reg_enabled(session_factory, user_id, enabled):
    async with session_factory() as sess:
        await UserRepository(sess).set_registration_notifications_enabled(user_id, enabled)
        await sess.commit()


async def _mark_sent(session_factory, user_id, comp_id, target):
    async with session_factory() as sess:
        await NotificationRepository(sess).mark_sent(user_id, comp_id, reg_reminder_kind(target))
        await sess.commit()


# ---------- 1h -> 30m, old reminder already sent ----------

async def test_interval_narrower_old_sent_still_reschedules(factory):
    session_factory, make_user = factory
    user, comp = await make_user()  # interval already 60

    await _mark_sent(session_factory, user.id, comp.id, notification_time(START, 60))
    await _set_interval(session_factory, user.telegram_id, 30)

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)

    # Two reminders at two distinct targets, both legitimate; the 30-minute
    # one must be (re)scheduled even though the 60-minute one already fired.
    assert _job_next_run(sched, user.id, comp.id) == notification_time(START, 30)


# ---------- 1h -> 1h replaces old, only current schedule stays ----------

async def test_interval_widens_replaces_old_schedule(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    sched = _FakeScheduler()
    await _set_interval(session_factory, user.telegram_id, 30)
    await reconcile_registration_reminders(sched, session_factory)
    assert _job_next_run(sched, user.id, comp.id) == notification_time(START, 30)

    await _set_interval(session_factory, user.telegram_id, 60)
    await reconcile_registration_reminders(sched, session_factory)

    # Replaced to the 60-minute target; exactly one job left.
    assert len(sched.jobs) == 1
    assert _job_next_run(sched, user.id, comp.id) == notification_time(START, 60)


# ---------- repeated change to the same interval -> no duplicates ----------

async def test_reconcile_is_idempotent(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    sched = _FakeScheduler()
    for _ in range(3):
        await reconcile_registration_reminders(sched, session_factory)

    assert len(sched.jobs) == 1
    assert _job_next_run(sched, user.id, comp.id) == notification_time(START, 60)


# ---------- target already passed -> no immediate overdue send ----------

async def test_past_target_after_interval_change_not_sent_immediately(factory):
    session_factory, make_user = factory
    now = datetime.now(timezone.utc)
    recent_start = now + timedelta(hours=2)  # registration 2h from now
    user, comp = await make_user(
        user_kwargs={"reg_reminder_interval": 30},
        comp_kwargs={"registration_start_at": recent_start},
    )

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 1  # 30-minute target is still ahead

    # Widen to 3h -> target is 1h in the past: must not fire retroactively.
    await _set_interval(session_factory, user.telegram_id, 180)
    await reconcile_registration_reminders(sched, session_factory)

    assert len(sched.jobs) == 0


# ---------- sent reminder with a different target does not block ----------

async def test_sent_reminder_does_not_block_different_target(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    t1 = notification_time(START, 60)
    t2 = notification_time(START, 30)
    assert t1 != t2
    assert reg_reminder_kind(t1) != reg_reminder_kind(t2)

    await _mark_sent(session_factory, user.id, comp.id, t1)

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 1


# ---------- disable cancels future job ----------

async def test_disabling_registration_cancels_future_job(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 1

    await _set_reg_enabled(session_factory, user.telegram_id, False)
    await reconcile_registration_reminders(sched, session_factory)

    assert len(sched.jobs) == 0


# ---------- re-enable recreates the reminder ----------

async def test_reenable_recreates_job(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    await _set_reg_enabled(session_factory, user.telegram_id, False)
    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 0

    await _set_reg_enabled(session_factory, user.telegram_id, True)
    await reconcile_registration_reminders(sched, session_factory)

    assert len(sched.jobs) == 1
    assert _job_next_run(sched, user.id, comp.id) == notification_time(START, 60)


# ---------- precision: target == start - interval, no scheduler shift ----------

async def test_target_is_exactly_start_minus_interval(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)

    assert _job_next_run(sched, user.id, comp.id) == START - timedelta(minutes=60)


def test_reg_reminder_kind_distinct_and_within_column():
    t1 = notification_time(START, 60)
    t2 = notification_time(START, 30)
    k1 = reg_reminder_kind(t1)
    k2 = reg_reminder_kind(t2)
    assert k1 != k2
    assert k1.startswith("reg_soon:")
    assert len(k1) <= 20  # fits the notifications.kind column
    assert reg_reminder_kind(None) == "reg_soon"


# ---------- cancelled competition never reminds ----------

async def test_cancelled_competition_removes_and_never_readds_job(factory):
    session_factory, make_user = factory
    user, comp = await make_user()

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 1  # a normal reminder was scheduled

    async with session_factory() as sess:
        db_comp = await sess.get(Competition, comp.id)
        db_comp.reg_status = "cancelled"
        await sess.commit()

    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 0  # cancelled -> job dropped, not re-added

    # Repeated reconcile stays clean (no resurrection, no error).
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 0


async def test_cancelled_competition_is_not_scheduled(factory):
    session_factory, make_user = factory
    user, comp = await make_user(comp_kwargs={"reg_status": "cancelled"})

    sched = _FakeScheduler()
    await reconcile_registration_reminders(sched, session_factory)
    assert len(sched.jobs) == 0
