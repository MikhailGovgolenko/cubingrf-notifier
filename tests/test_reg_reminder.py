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
from cubingrf_notifier.notifications.reg_reminder import should_send_registration_reminder
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


# ---------- scheduling decision ----------

def test_reminder_exactly_30_minutes_before():
    now = _utc(2026, 8, 16, 7, 0)
    start = now + timedelta(minutes=30)
    assert should_send_registration_reminder(start, now) is True


def test_reminder_within_window_does_not_repeat():
    now = _utc(2026, 8, 16, 7, 0)
    start = now + timedelta(minutes=29)
    assert should_send_registration_reminder(start, now) is True


def test_reminder_outside_window():
    now = _utc(2026, 8, 16, 7, 0)
    assert should_send_registration_reminder(now + timedelta(minutes=31), now) is False
    assert should_send_registration_reminder(now, now) is False
    assert should_send_registration_reminder(now - timedelta(minutes=1), now) is False


def test_reminder_missing_time():
    assert should_send_registration_reminder(None, _utc(2026, 8, 16, 7, 0)) is False


def test_reminder_naive_dates_treated_as_utc():
    now = _utc(2026, 8, 16, 7, 0)
    start_naive = datetime(2026, 8, 16, 7, 30)
    assert should_send_registration_reminder(start_naive, now) is True


def test_reminder_not_sent_after_scheduler_downtime():
    now = _utc(2026, 8, 16, 7, 0)
    start = now - timedelta(minutes=25)
    assert should_send_registration_reminder(start, now) is False


def test_reminder_same_instant_any_timezone():
    now = _utc(2026, 8, 16, 7, 5)
    start_utc = _utc(2026, 8, 16, 7, 30)
    start_msk = datetime(2026, 8, 16, 10, 30, tzinfo=timezone(timedelta(hours=3)))
    assert should_send_registration_reminder(start_utc, now) is True
    assert should_send_registration_reminder(start_msk, now) is True


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
    start = _utc(2026, 8, 16, 7, 0)
    comp = Competition(external_id="RT", name="", registration_start_at=start)
    db_session.add(comp)
    await db_session.commit()
    await db_session.refresh(comp)

    now = _utc(2026, 8, 16, 6, 45)
    assert should_send_registration_reminder(comp.registration_start_at, now) is True
    assert should_send_registration_reminder(comp.registration_start_at, start) is False