import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import (
    CompetitionRepository,
    UserRepository,
    RoundResultRepository,
)
from cubingrf_notifier.competitions.models import CompetitionDTO
from cubingrf_notifier.i18n import DEFAULT_LANGUAGE


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
    await engine.dispose()


# --- register_user (username + auto-detected language) ---

async def test_register_user_creates_with_username_and_language(session):
    repo = UserRepository(session)
    user = await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert user.username == "alex"
    assert user.language == "en"
    assert await repo.get_user_language(111) == "en"


async def test_register_user_detects_russian(session):
    repo = UserRepository(session)
    await repo.register_user(222, username="иван", language_code="ru")
    await session.flush()
    assert await repo.get_user_language(222) == "ru"


async def test_register_user_defaults_to_english_without_code(session):
    repo = UserRepository(session)
    await repo.register_user(333, username="bot", language_code=None)
    await session.flush()
    user = await repo.get_user_by_telegram_id(333)
    assert user.language == "en"
    assert await repo.get_user_language(333) == "en"


async def test_register_user_refreshes_username_for_existing(session):
    repo = UserRepository(session)
    await repo.register_user(444, username="old_name", language_code="en")
    await session.flush()
    await repo.register_user(444, username="new_name", language_code="en")
    await session.flush()
    user = await repo.get_user_by_telegram_id(444)
    assert user.username == "new_name"


async def test_register_user_keeps_manually_chosen_language(session):
    repo = UserRepository(session)
    await repo.register_user(555, username="alex", language_code="en")
    await repo.set_user_language(555, "ru")
    await session.flush()
    await repo.register_user(555, username="alex", language_code="en")
    await session.flush()
    assert await repo.get_user_language(555) == "ru"


async def test_get_user_language_unregistered_returns_default(session):
    repo = UserRepository(session)
    assert await repo.get_user_language(999) == DEFAULT_LANGUAGE


# --- sync_username (refresh from any interaction) ---

async def test_sync_username_updates_existing_user(session):
    repo = UserRepository(session)
    await repo.create_user(111)
    await session.flush()
    assert await repo.sync_username(111, "alex") is True
    assert (await repo.get_user_by_telegram_id(111)).username == "alex"


async def test_sync_username_fills_missing_username(session):
    repo = UserRepository(session)
    user = await repo.register_user(111, username=None, language_code="en")
    await session.flush()
    assert user.username is None
    assert await repo.sync_username(111, "alex") is True
    assert (await repo.get_user_by_telegram_id(111)).username == "alex"


async def test_sync_username_noop_when_unchanged(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert await repo.sync_username(111, "alex") is False


async def test_sync_username_ignores_unknown_user(session):
    repo = UserRepository(session)
    assert await repo.sync_username(999, "alex") is False


async def test_sync_username_ignores_empty_username(session):
    repo = UserRepository(session)
    await repo.create_user(111)
    await session.flush()
    assert await repo.sync_username(111, "") is False
    assert (await repo.get_user_by_telegram_id(111)).username is None


async def test_sync_username_preserves_language(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.set_user_language(111, "ru")
    await session.flush()
    assert await repo.sync_username(111, "new_name") is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.username == "new_name"
    assert user.language == "ru"


# --- blocked_at (active / blocked tracking) ---

async def test_new_user_is_active(session):
    repo = UserRepository(session)
    user = await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert user.blocked_at is None


async def test_set_blocked_marks_user(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert await repo.set_blocked(111) is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.blocked_at is not None


async def test_set_blocked_keeps_user_in_db(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    await repo.set_blocked(111)
    await session.flush()
    assert await repo.get_user_by_telegram_id(111) is not None
    assert len(await repo.list_enabled_users()) == 0


async def test_set_blocked_noop_when_already_blocked(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.set_blocked(111)
    await session.flush()
    assert await repo.set_blocked(111) is False


async def test_mark_active_clears_blocked_at(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.set_blocked(111)
    await session.flush()
    assert await repo.mark_active(111) is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.blocked_at is None
    assert [u.telegram_id for u in await repo.list_enabled_users()] == [111]


async def test_mark_active_noop_when_already_active(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert await repo.mark_active(111) is False


async def test_list_enabled_users_excludes_blocked(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.register_user(222, username="bob", language_code="en")
    await session.flush()
    await repo.set_blocked(111)
    await session.flush()
    enabled = [u.telegram_id for u in await repo.list_enabled_users()]
    assert enabled == [222]


# --- last_seen_at (activity tracking) ---

async def test_new_user_gets_last_seen_at(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert (await repo.get_user_by_telegram_id(111)).last_seen_at is not None


async def test_mark_seen_updates_last_seen_at(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    first = (await repo.get_user_by_telegram_id(111)).last_seen_at
    assert await repo.mark_seen(111, "alex") is True
    assert (await repo.get_user_by_telegram_id(111)).last_seen_at is not None


async def test_mark_seen_works_without_username(session):
    repo = UserRepository(session)
    await repo.register_user(111, username=None, language_code="en")
    await session.flush()
    assert await repo.mark_seen(111) is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.last_seen_at is not None
    assert user.username is None


async def test_mark_seen_ignores_unknown_user(session):
    repo = UserRepository(session)
    assert await repo.mark_seen(999, "alex") is False


async def test_mark_seen_clears_blocked_at(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.set_blocked(111)
    await session.flush()
    assert await repo.mark_seen(111, "alex") is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.blocked_at is None
    assert user.last_seen_at is not None


async def test_mark_seen_updates_username_preserves_language(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await repo.set_user_language(111, "ru")
    await session.flush()
    assert await repo.mark_seen(111, "new_name") is True
    user = await repo.get_user_by_telegram_id(111)
    assert user.username == "new_name"
    assert user.language == "ru"


# --- per-type notification preferences ---

async def test_new_user_has_default_notification_preferences(session):
    repo = UserRepository(session)
    user = await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    assert user.announcements_enabled is True
    assert user.registration_notifications_enabled is True
    assert user.reg_reminder_interval == 30


async def test_set_announcements_enabled(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    await repo.set_announcements_enabled(111, False)
    await session.flush()
    assert (await repo.get_user_by_telegram_id(111)).announcements_enabled is False


async def test_set_registration_notifications_enabled(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    await repo.set_registration_notifications_enabled(111, False)
    await session.flush()
    assert (await repo.get_user_by_telegram_id(111)).registration_notifications_enabled is False


async def test_set_reg_reminder_interval(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="alex", language_code="en")
    await session.flush()
    await repo.set_reg_reminder_interval(111, 1440)
    await session.flush()
    assert (await repo.get_reg_reminder_interval(111)) == 1440


async def test_get_reg_reminder_interval_unregistered_returns_default(session):
    repo = UserRepository(session)
    assert await repo.get_reg_reminder_interval(999) == 30


# --- list_upcoming_competitions (date-driven availability filter) ---

def _future_days(n: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=n)


def _past_days(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


async def _add_comp(session, ext_id, date, reg_status=None, end_date=None,
                    registration_start_at=None):
    dto = CompetitionDTO(
        external_id=ext_id,
        name=ext_id,
        date=date,
        end_date=end_date,
        reg_status=reg_status,
        registration_start_at=registration_start_at,
    )
    return await CompetitionRepository(session).add_competition(dto)


async def test_list_upcoming_includes_open_and_scheduled_future(session):
    await _add_comp(session, "Open", _future_days(7), reg_status="open")
    await _add_comp(session, "Scheduled", _future_days(9), reg_status="scheduled")
    await session.flush()
    names = [c.name for c in await CompetitionRepository(session).list_upcoming_competitions()]
    assert names == ["Open", "Scheduled"]


async def test_list_upcoming_includes_unknown_status_with_future_registration(session):
    await _add_comp(
        session, "UnknownFutureReg", _future_days(6),
        reg_status=None,
        registration_start_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    await session.flush()
    names = [c.name for c in await CompetitionRepository(session).list_upcoming_competitions()]
    assert names == ["UnknownFutureReg"]


async def test_list_upcoming_includes_unknown_status_with_opened_registration(session):
    await _add_comp(
        session, "UnknownOpenReg", _future_days(6),
        reg_status=None,
        registration_start_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    await session.flush()
    names = [c.name for c in await CompetitionRepository(session).list_upcoming_competitions()]
    assert names == ["UnknownOpenReg"]


async def test_list_upcoming_excludes_started_competition(session):
    await _add_comp(session, "Started", _past_days(1), reg_status="open")
    await session.flush()
    assert await CompetitionRepository(session).list_upcoming_competitions() == []


async def test_list_upcoming_excludes_finished_competition(session):
    await _add_comp(
        session, "Finished", _future_days(1),
        reg_status="open",
        end_date=_past_days(1),
    )
    await session.flush()
    assert await CompetitionRepository(session).list_upcoming_competitions() == []


async def test_list_upcoming_excludes_closed_future(session):
    await _add_comp(session, "Closed", _future_days(5), reg_status="closed")
    await session.flush()
    assert await CompetitionRepository(session).list_upcoming_competitions() == []


async def test_list_upcoming_excludes_unknown_status_without_dates(session):
    await _add_comp(session, "UnknownNoReg", _future_days(5), reg_status=None)
    await session.flush()
    assert await CompetitionRepository(session).list_upcoming_competitions() == []


async def test_list_upcoming_excludes_missing_date(session):
    await _add_comp(session, "NoDate", None, reg_status="open")
    await session.flush()
    assert await CompetitionRepository(session).list_upcoming_competitions() == []


async def test_list_upcoming_orders_by_date(session):
    await _add_comp(session, "Later", _future_days(10), reg_status="open")
    await _add_comp(session, "Sooner", _future_days(5), reg_status="open")
    await session.flush()
    names = [c.name for c in await CompetitionRepository(session).list_upcoming_competitions()]
    assert names == ["Sooner", "Later"]


# --- RSF ID ---

async def test_set_and_get_rsf_id(session):
    repo = UserRepository(session)
    await repo.create_user(111)
    await session.flush()
    assert await repo.get_rsf_id(111) is None
    await repo.set_rsf_id(111, "AS03")
    await session.flush()
    assert await repo.get_rsf_id(111) == "AS03"


async def test_set_rsf_id_returns_none_for_unknown_user(session):
    repo = UserRepository(session)
    assert await repo.set_rsf_id(999, "AS03") is None


async def test_clear_rsf_id(session):
    repo = UserRepository(session)
    await repo.create_user(111)
    await repo.set_rsf_id(111, "AS03")
    await repo.set_rsf_id(111, None)
    await session.flush()
    assert await repo.get_rsf_id(111) is None


async def test_elegible_users_require_rsf_and_switches(session):
    repo = UserRepository(session)
    await repo.register_user(111, username="a", language_code="en")
    await repo.register_user(222, username="b", language_code="en")
    await repo.set_rsf_id(111, "AS03")
    await session.flush()
    ids = [u.telegram_id for u in await repo.list_result_tracking_users()]
    # 111 has rsf but result switch defaults to true; 222 has no rsf.
    assert 111 in ids
    assert 222 not in ids

    await repo.set_result_notifications_enabled(111, False)
    await session.flush()
    ids = [u.telegram_id for u in await repo.list_result_tracking_users()]
    assert 111 not in ids


# --- RoundResultRepository ---

def _add_comp_for_state(session):
    return CompetitionRepository(session).add_competition(
        CompetitionDTO(external_id="SPB", name="SPB", date=_future_days(1), reg_status="open")
    )


async def test_get_or_create_state_creates_then_returns(session):
    user = await UserRepository(session).create_user(111)
    comp = await _add_comp_for_state(session)
    await session.flush()

    rrs = RoundResultRepository(session)
    s1 = await rrs.get_or_create_state(user.id, comp.id, "333", 1)
    s2 = await rrs.get_or_create_state(user.id, comp.id, "333", 1)
    await session.flush()
    assert s1.id == s2.id
    assert s1.completed is False
    assert s1.notified is False


async def test_list_tracked_competition_ids(session):
    user = await UserRepository(session).create_user(111)
    comp = await _add_comp_for_state(session)
    comp2 = await CompetitionRepository(session).add_competition(
        CompetitionDTO(external_id="SPB2", name="SPB2", date=_future_days(2), reg_status="open")
    )
    await session.flush()

    rrs = RoundResultRepository(session)
    await rrs.get_or_create_state(user.id, comp.id, "333", 1)
    await rrs.get_or_create_state(user.id, comp2.id, "222", 1)
    await session.flush()
    tracked = await rrs.list_tracked_competition_ids()
    assert sorted(tracked) == sorted([comp.id, comp2.id])


async def test_list_active_competition_ids_window(session):
    await _add_comp(session, "Recent", _future_days(3), reg_status="open")
    await _add_comp(session, "Old", _past_days(30), reg_status="open")
    await session.flush()
    ids = await CompetitionRepository(session).list_active_competition_ids(lookback_days=2, lookahead_days=14)
    comps = []
    for cid in ids:
        c = await CompetitionRepository(session).get_by_id(cid)
        comps.append(c.name)
    assert comps == ["Recent"]