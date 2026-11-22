"""Integration coverage for the schedule-based completion heuristic."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.competitions.models import CompetitionDTO
from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import (
    CompetitionRepository,
    RoundResultRepository,
    UserRepository,
)
from cubingrf_notifier.results.models import RoundResult, RoundRoster, RoundSnapshot
from cubingrf_notifier.results.service import RoundResultService


@pytest.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


class FakeScraper:
    def __init__(self, schedule, results):
        self.schedule = schedule
        self.results = results  # {(event, round): list[RoundResult]}

    async def get_schedule(self, competition_id):
        return self.schedule

    async def get_round_pairs(self, competition_id):
        return list(self.schedule)

    async def get_registrant_mapping(self, competition_id):
        return {"RSF1": 1}

    async def fetch_round_results(self, competition_id, event, round_number):
        return list(self.results.get((event, round_number), []))

    async def fetch_round_roster(self, competition_id, event, round_number, mapping=None):
        # Deliberately incomplete roster: two rostered, only one result row.
        return RoundRoster(registrant_ids=(1, 2), count=2)


class FakeNotifier:
    def __init__(self):
        self.sent = []

    async def send_round_result(self, telegram_id, **kwargs):
        self.sent.append((kwargs["event_code"], kwargs["round_number"], kwargs["edited"]))


def _result(rid=1):
    return RoundResult(
        registrant_id=rid,
        place=1,
        attempts=(900, 900, 900, 900, 900),
        average=900,
        best=900,
    )


async def _seed(session):
    user_repo = UserRepository(session)
    user = await user_repo.create_user(100)
    user.rsf_id = "RSF1"
    user.result_notifications_enabled = True
    user.notifications_enabled = True

    dto = CompetitionDTO(
        external_id="TEST2026",
        name="Test Open",
        date=datetime.now(timezone.utc) + timedelta(days=1),
        reg_status="open",
    )
    comp = await CompetitionRepository(session).add_competition(dto)
    await session.flush()
    return user, comp


async def test_earlier_round_notified_despite_incomplete_roster(session_maker):
    """A later round's first result implies earlier schedule rounds are done."""
    schedule = [("333", 1), ("333", 2)]
    notifier = FakeNotifier()
    # Round 2 already has its first result; round 1 still has none.
    scraper = FakeScraper(schedule, {("333", 2): [_result()]})

    async with session_maker() as session:
        user, comp = await _seed(session)
        service = RoundResultService(session, scraper=scraper, notifier=notifier)
        # First tick: round 2's result marks round 1 as completed.
        await service.poll()
        assert notifier.sent == []

        # Second tick: round 1 now has a result, but its roster is still
        # incomplete. Simulate a later tick so the poll backoff allows it.
        states = await RoundResultRepository(session).get_states_for_user(user.id, comp.id)
        for state in states:
            state.last_checked_at = datetime.now(timezone.utc) - timedelta(minutes=2)
            state.completed_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        scraper.results[("333", 1)] = [_result()]
        notifier = FakeNotifier()
        service = RoundResultService(session, scraper=scraper, notifier=notifier)
        await service.poll()

    assert notifier.sent == [("333", 1, False)]


async def test_placeholder_rows_do_not_mark_earlier_round_complete(session_maker):
    """Placeholder result rows with no attempts are not a first entered result."""
    schedule = [("333", 1), ("333", 2)]
    notifier = FakeNotifier()
    placeholder = RoundResult(registrant_id=1, place=0, attempts=())
    scraper = FakeScraper(schedule, {("333", 2): [placeholder], ("333", 1): [_result()]})

    async with session_maker() as session:
        user, comp = await _seed(session)
        service = RoundResultService(session, scraper=scraper, notifier=notifier)
        await service.poll()

        states = {
            (s.event_code, s.round_number): s
            for s in await RoundResultRepository(session).get_states_for_user(user.id, comp.id)
        }
        assert ("333", 1) in states  # state created, but...
        assert states[("333", 1)].completed is False  # ...not marked complete
        assert notifier.sent == []


async def test_no_schedule_falls_back_to_roster_check(session_maker):
    """Without a schedule the old fail-safe behaviour is unchanged."""
    notifier = FakeNotifier()
    scraper = FakeScraper([], {("333", 1): [_result()], ("333", 2): [_result()]})

    async with session_maker() as session:
        await _seed(session)
        service = RoundResultService(session, scraper=scraper, notifier=notifier)
        await service.poll()

    assert notifier.sent == []
