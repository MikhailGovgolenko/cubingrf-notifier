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


# ---------- recipients: region / discipline / disabled ----------

def _comp(location="Москва, Москва", disciplines=("333", "444")):
    return SimpleNamespace(location=location, disciplines=list(disciplines))


def _user(regions=(), disciplines=(), enabled=True):
    return SimpleNamespace(
        notifications_enabled=enabled,
        regions=[SimpleNamespace(region_key=r) for r in regions],
        disciplines=[SimpleNamespace(discipline_code=c) for c in disciplines],
    )


def test_reminder_region_matches_gets_it():
    assert should_notify_user(_user(regions=["Москва"]), _comp()) is True


def test_reminder_region_mismatch_skips():
    assert should_notify_user(_user(regions=["Красноярский край"]), _comp()) is False


def test_reminder_discipline_matches_gets_it():
    assert should_notify_user(_user(disciplines=["333"]), _comp()) is True


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
    assert "🔔 Регистрация откроется через 30 минут!" in ru
    assert "🔔 Registration opens in 30 minutes!" in en
    assert "🏆 Moscow Open" in ru
    assert "🏆 Moscow Open" in en


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