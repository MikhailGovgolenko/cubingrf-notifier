from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from cubingrf_notifier.database.models import Base, Notification, User, Competition
from cubingrf_notifier.database.repository import (
    NotificationRepository,
    KIND_REG_SOON,
    KIND_NEW,
)
from cubingrf_notifier.notifications.reg_reminder import (
    should_send_registration_reminder,
    notification_time,
)
from cubingrf_notifier.notifications.competition_formatter import format_registration_reminder
from cubingrf_notifier.notifications.matcher import should_notify_user


def _utc(*args, **kwargs):
    return datetime(*args, tzinfo=timezone.utc, **kwargs)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as s:
        yield s
    await engine.dispose()


# ---------- exact scheduled time ----------

def test_notification_time_exact_instants():
    start = _utc(2026, 8, 16, 18, 0)
    assert notification_time(start, 60) == _utc(2026, 8, 16, 17, 0)
    assert notification_time(start, 30) == _utc(2026, 8, 16, 17, 30)
    assert notification_time(start, 180) == _utc(2026, 8, 16, 15, 0)


def test_notification_time_missing_start_is_none():
    assert notification_time(None, 60) is None


def test_notification_time_naive_treated_as_utc():
    start = datetime(2026, 8, 16, 18, 0)
    assert notification_time(start, 60) == _utc(2026, 8, 16, 17, 0)


def test_notification_time_offset_timezone_instant():
    start = datetime(2026, 8, 16, 21, 0, tzinfo=timezone(timedelta(hours=3)))
    assert notification_time(start, 60) == _utc(2026, 8, 16, 17, 0)


def test_notification_time_crossing_midnight():
    start = _utc(2026, 8, 17, 0, 30)
    assert notification_time(start, 60) == _utc(2026, 8, 16, 23, 30)
    start2 = _utc(2026, 8, 17, 1, 0)
    assert notification_time(start2, 30) == _utc(2026, 8, 17, 0, 30)


def test_notification_time_crossing_day_boundary_with_days():
    start = _utc(2026, 8, 18, 6, 0)
    assert notification_time(start, 1440) == _utc(2026, 8, 17, 6, 0)


# ---------- scheduling decision (exact instant, not a window) ----------

def test_reminder_not_sent_before_target():
    start = _utc(2026, 8, 16, 18, 0)
    before = _utc(2026, 8, 16, 16, 59)
    assert should_send_registration_reminder(start, before, 60) is False


def test_reminder_sent_at_target_instant():
    start = _utc(2026, 8, 16, 18, 0)
    at_target = _utc(2026, 8, 16, 17, 0)
    assert should_send_registration_reminder(start, at_target, 60) is True


def test_reminder_before_target_other_interval():
    start = _utc(2026, 8, 16, 18, 0)
    assert should_send_registration_reminder(start, _utc(2026, 8, 16, 17, 29), 30) is False
    assert should_send_registration_reminder(start, _utc(2026, 8, 16, 17, 30), 30) is True


def test_reminder_not_sent_after_registration_started():
    start = _utc(2026, 8, 16, 18, 0)
    assert should_send_registration_reminder(start, _utc(2026, 8, 16, 18, 0), 60) is False
    assert should_send_registration_reminder(start, _utc(2026, 8, 16, 18, 1), 60) is False


def test_reminder_missing_time():
    assert should_send_registration_reminder(None, _utc(2026, 8, 16, 7, 0), 60) is False


def test_reminder_naive_dates_treated_as_utc():
    start = datetime(2026, 8, 16, 18, 0)
    assert should_send_registration_reminder(start, _utc(2026, 8, 16, 17, 0), 60) is True


def test_reminder_same_instant_any_timezone():
    start_utc = _utc(2026, 8, 16, 18, 0)
    start_msk = datetime(2026, 8, 16, 21, 0, tzinfo=timezone(timedelta(hours=3)))
    for start in (start_utc, start_msk):
        assert should_send_registration_reminder(start, _utc(2026, 8, 16, 17, 0), 60) is True
        assert should_send_registration_reminder(start, _utc(2026, 8, 16, 16, 59), 60) is False


def test_start_at_differ_compares_utc_instants():
    from cubingrf_notifier.competitions.service import _start_at_differ

    a = _utc(2026, 8, 16, 7, 0)
    assert _start_at_differ(None, a) is True
    assert _start_at_differ(a, None) is True
    assert _start_at_differ(a, a) is False
    assert _start_at_differ(a, a + timedelta(hours=2)) is True
    msk_same = datetime(2026, 8, 16, 10, 0, tzinfo=timezone(timedelta(hours=3)))
    assert _start_at_differ(a, msk_same) is False
    assert _start_at_differ(datetime(2026, 8, 16, 7, 0), a) is True


# ---------- recipients: region / discipline / disabled ----------

def _comp(location="Москва, Москва", disciplines=("333", "444")):
    return SimpleNamespace(location=location, disciplines=list(disciplines))


def _user(regions=(), events=(), enabled=True):
    return SimpleNamespace(
        notifications_enabled=enabled,
        regions=[SimpleNamespace(region_key=r) for r in regions],
        events=[SimpleNamespace(event_code=c) for c in events],
    )


def test_reminder_region_matches_gets_it():
    assert should_notify_user(_user(regions=["Москва"]), _comp()) is True


def test_reminder_region_mismatch_skips():
    assert should_notify_user(_user(regions=["Красноярский край"]), _comp()) is False


def test_reminder_discipline_matches_gets_it():
    assert should_notify_user(_user(events=["333"]), _comp()) is True


def test_reminder_disabled_skips():
    assert should_notify_user(_user(enabled=False), _comp()) is False


def _full_comp():
    return SimpleNamespace(
        name="Moscow Open",
        date=_utc(2026, 8, 29, 8, 0),
        end_date=None,
        location="Москва, Москва",
        disciplines=["333", "444"],
        reg_status="scheduled",
        url="https://cubingrf.org/competitions/MoscowOpen2026",
    )


def test_reminder_language_ru_and_en():
    ru = format_registration_reminder(_full_comp(), "ru")
    en = format_registration_reminder(_full_comp(), "en")
    assert "🔔 Регистрация откроется скоро!" in ru
    assert "🔔 Registration opens soon!" in en
    assert '<b><a href="https://cubingrf.org/competitions/MoscowOpen2026">Moscow Open</a></b>' in ru
    assert '<b><a href="https://cubingrf.org/competitions/MoscowOpen2026">Moscow Open</a></b>' in en


# ---------- deduplication per kind ----------

async def test_mark_sent_unique_per_kind(db_session):
    user = User(telegram_id=111, language="ru")
    comp = Competition(external_id="Z", name="")
    db_session.add_all([user, comp])
    await db_session.flush()

    repo = NotificationRepository(db_session)
    await repo.mark_sent(user.id, comp.id, KIND_REG_SOON)
    await repo.mark_sent(user.id, comp.id, KIND_REG_SOON)
    await repo.mark_sent(user.id, comp.id, KIND_NEW)
    await db_session.commit()

    res = await db_session.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id,
            Notification.competition_id == comp.id,
        )
    )
    assert res.scalar_one() == 2  # one 'reg_soon', one 'new', no duplicates


async def test_was_sent_distinguishes_kind(db_session):
    user = User(telegram_id=222, language="ru")
    comp = Competition(external_id="Y", name="")
    db_session.add_all([user, comp])
    await db_session.flush()

    repo = NotificationRepository(db_session)
    await repo.mark_sent(user.id, comp.id, KIND_NEW)
    await db_session.commit()

    assert await repo.was_sent(user.id, comp.id, KIND_NEW) is True
    assert await repo.was_sent(user.id, comp.id, KIND_REG_SOON) is False


async def test_reminder_dedup_survives_start_at_change(db_session):
    user = User(telegram_id=333, language="ru")
    comp = Competition(external_id="C1", name="", registration_start_at=_utc(2026, 8, 16, 10, 0))
    db_session.add_all([user, comp])
    await db_session.flush()

    repo = NotificationRepository(db_session)
    await repo.mark_sent(user.id, comp.id, KIND_REG_SOON)
    await db_session.commit()

    comp.registration_start_at = _utc(2026, 8, 16, 12, 0)
    await db_session.flush()

    assert await repo.was_sent(user.id, comp.id, KIND_REG_SOON) is True


async def test_reminders_independent_between_competitions(db_session):
    user = User(telegram_id=444, language="ru")
    c1 = Competition(external_id="A", name="")
    c2 = Competition(external_id="B", name="")
    db_session.add_all([user, c1, c2])
    await db_session.flush()

    repo = NotificationRepository(db_session)
    await repo.mark_sent(user.id, c1.id, KIND_REG_SOON)
    await db_session.commit()

    assert await repo.was_sent(user.id, c1.id, KIND_REG_SOON) is True
    assert await repo.was_sent(user.id, c2.id, KIND_REG_SOON) is False


async def test_registration_start_roundtrip_preserves_instant(db_session):
    # SQLite stores naive datetimes; after a round-trip the value is naive but
    # the reminder logic must still treat it as UTC.
    start = _utc(2026, 8, 16, 7, 0)
    comp = Competition(external_id="RT", name="", registration_start_at=start)
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    assert should_send_registration_reminder(comp.registration_start_at, _utc(2026, 8, 16, 5, 59), 60) is False
    assert should_send_registration_reminder(comp.registration_start_at, _utc(2026, 8, 16, 6, 0), 60) is True
    assert should_send_registration_reminder(comp.registration_start_at, _utc(2026, 8, 16, 7, 0), 60) is False