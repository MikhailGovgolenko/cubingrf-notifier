import pytest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import CompetitionRepository
from cubingrf_notifier.competitions.models import CompetitionDTO
from cubingrf_notifier.competitions.service import CompetitionService, _mark_cancelled_once


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
    await engine.dispose()


class FakeSource:
    def __init__(self, dtos):
        self.dtos = dtos
        self.calls = 0

    async def fetch_competitions(self):
        self.calls += 1
        return list(self.dtos)


def _dto(ext_id, reg_status, name_en=None):
    return CompetitionDTO(
        external_id=ext_id,
        name=ext_id,
        name_en=name_en,
        date=datetime(2026, 11, 1, tzinfo=timezone.utc),
        reg_status=reg_status,
    )


async def _get(session, ext_id):
    return await CompetitionRepository(session).get_by_external_id(ext_id)


async def test_new_cancelled_competition_is_stamped(session):
    source = FakeSource([_dto("Cup", "cancelled")])
    service = CompetitionService(source, session)
    new = await service.check_new_competitions()
    await session.flush()
    assert len(new) == 1
    comp = await _get(session, "Cup")
    assert comp.reg_status == "cancelled"
    assert comp.cancelled_at is not None


async def test_transition_to_cancelled_stamps_once_and_never_resets(session):
    source = FakeSource([_dto("Cup", "open")])
    service = CompetitionService(source, session)
    await service.check_new_competitions()
    await session.flush()

    source.dtos = [_dto("Cup", "cancelled")]
    await service.check_new_competitions()
    await session.flush()
    first = (await _get(session, "Cup")).cancelled_at
    assert first is not None

    # A later scrape that still reports cancelled must not reset the timestamp.
    source.dtos = [_dto("Cup", "cancelled")]
    await service.check_new_competitions()
    await session.flush()
    second = (await _get(session, "Cup")).cancelled_at
    assert second == first


async def test_legacy_cancelled_without_timestamp_is_stamped(session):
    """A competition already cancelled before the upgrade gets a timestamp on
    the first run of the new service, starting a fresh 24h window."""
    await CompetitionRepository(session).add_competition(_dto("Legacy", "cancelled"))
    await session.flush()

    source = FakeSource([_dto("Legacy", "cancelled")])
    service = CompetitionService(source, session)
    await service.check_new_competitions()
    await session.flush()
    assert (await _get(session, "Legacy")).cancelled_at is not None


def test_mark_cancelled_once_noop_for_non_cancelled():
    class C:
        reg_status = "open"
        cancelled_at = None
    comp = C()
    assert _mark_cancelled_once(comp, now=datetime(2026, 8, 14, tzinfo=timezone.utc)) is False
    assert comp.cancelled_at is None


def test_mark_cancelled_once_ignores_existing_timestamp():
    class C:
        reg_status = "cancelled"
        cancelled_at = datetime(2026, 8, 10, tzinfo=timezone.utc)
    comp = C()
    assert _mark_cancelled_once(comp, now=datetime(2026, 8, 14, tzinfo=timezone.utc)) is False
    assert comp.cancelled_at == datetime(2026, 8, 10, tzinfo=timezone.utc)


async def test_new_competition_persists_name_en(session):
    source = FakeSource([_dto("Cup", "scheduled", name_en="Russia Speedcubing Cup V 2026")])
    service = CompetitionService(source, session)
    new = await service.check_new_competitions()
    await session.flush()
    assert len(new) == 1
    comp = await _get(session, "Cup")
    assert comp.name_en == "Russia Speedcubing Cup V 2026"


async def test_existing_competition_name_en_is_refreshed(session):
    source = FakeSource([_dto("Cup", "open")])
    service = CompetitionService(source, session)
    await service.check_new_competitions()
    await session.flush()
    assert (await _get(session, "Cup")).name_en is None

    source.dtos = [_dto("Cup", "open", name_en="Russia Speedcubing Cup V 2026")]
    await service.check_new_competitions()
    await session.flush()
    assert (await _get(session, "Cup")).name_en == "Russia Speedcubing Cup V 2026"


async def test_existing_competition_name_en_is_not_wiped(session):
    source = FakeSource([_dto("Cup", "open", name_en="Russia Speedcubing Cup V 2026")])
    service = CompetitionService(source, session)
    await service.check_new_competitions()
    await session.flush()

    # A scrape that fails to provide the English name must not clear it.
    source.dtos = [_dto("Cup", "open")]
    await service.check_new_competitions()
    await session.flush()
    assert (await _get(session, "Cup")).name_en == "Russia Speedcubing Cup V 2026"
