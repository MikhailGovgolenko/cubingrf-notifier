import pytest
from types import SimpleNamespace
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base, User
from cubingrf_notifier.database.repository import UserRepository
from cubingrf_notifier.competitions.regions import REGION_LABELS, ALL_REGION_KEYS, region_key_from_location
from cubingrf_notifier.bot.competitions import filter_competitions
from cubingrf_notifier.bot.keyboards import regions_keyboard


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
    await engine.dispose()


def _comp(location="Москва, Москва", disciplines=None):
    return SimpleNamespace(
        location=location,
        disciplines=disciplines or [],
        date=datetime(2026, 8, 7),
        name="Comp",
        url="https://example.com",
        reg_status="open",
    )


# --- region catalog ---

def test_region_key_from_location_simple():
    assert region_key_from_location("Новосибирская область, Новосибирск") == "Новосибирская область"


def test_region_key_from_location_moscow_union():
    assert region_key_from_location("Москва, Москва") == "Москва"
    assert region_key_from_location("Московская область, Щёлково") == "Москва"


def test_region_key_from_location_unknown_preserved():
    assert region_key_from_location("Какой-то край, Город") == "Какой-то край"


def test_region_key_from_location_none_and_empty():
    assert region_key_from_location(None) is None
    assert region_key_from_location("") is None


def test_all_region_keys_and_labels_match():
    assert len(ALL_REGION_KEYS) > 0
    for key in ALL_REGION_KEYS:
        assert REGION_LABELS[key] == key


# --- repository persistence ---

async def test_save_and_read_regions(session):
    repo = UserRepository(session)
    user = await repo.create_user(111)
    await session.flush()

    await repo.set_user_regions(111, ["Москва", "Санкт-Петербург"])
    await session.flush()
    assert sorted(await repo.get_user_regions(111)) == ["Москва", "Санкт-Петербург"]


async def test_save_regions_replaces_existing(session):
    repo = UserRepository(session)
    await repo.create_user(222)
    await session.flush()

    await repo.set_user_regions(222, ["Москва", "Омская область"])
    await repo.set_user_regions(222, ["Республика Коми"])
    await session.flush()
    assert await repo.get_user_regions(222) == ["Республика Коми"]


async def test_save_empty_regions_clears(session):
    repo = UserRepository(session)
    await repo.create_user(333)
    await session.flush()

    await repo.set_user_regions(333, ["Москва"])
    await repo.set_user_regions(333, [])
    await session.flush()
    assert await repo.get_user_regions(333) == []


async def test_get_regions_for_unregistered_user(session):
    repo = UserRepository(session)
    assert await repo.get_user_regions(999) == []


# --- competition filtering ---

def test_filter_no_filters_keeps_all():
    comps = [_comp(location="Москва, Москва", disciplines=["333"]),
             _comp(location="Омская область, Омск", disciplines=["222"])]
    assert len(filter_competitions(comps)) == 2


def test_filter_by_regions_only():
    comps = [_comp(location="Москва, Москва"),
             _comp(location="Московская область, Щёлково"),
             _comp(location="Омская область, Омск")]
    out = filter_competitions(comps, region_keys=["Москва"])
    assert {c.location for c in out} == {"Москва, Москва", "Московская область, Щёлково"}


def test_filter_by_disciplines_only():
    comps = [_comp(disciplines=["333"]), _comp(disciplines=["222"])]
    out = filter_competitions(comps, event_codes=["333"])
    assert len(out) == 1
    assert out[0].disciplines == ["333"]


def test_filter_combined_region_and_discipline():
    comps = [
        _comp(location="Москва, Москва", disciplines=["333"]),
        _comp(location="Москва, Москва", disciplines=["222"]),
        _comp(location="Омская область, Омск", disciplines=["333"]),
    ]
    out = filter_competitions(comps, event_codes=["333"], region_keys=["Москва"])
    assert len(out) == 1
    assert out[0].location == "Москва, Москва"


# --- regions keyboard ---

def test_regions_keyboard_vertical_per_row():
    kb = regions_keyboard([])
    rows = kb.inline_keyboard
    for i, key in enumerate(ALL_REGION_KEYS):
        row = rows[i]
        assert len(row) == 1
        assert row[0].callback_data == f"region:toggle:{key}"


def test_regions_keyboard_checkmarks():
    kb = regions_keyboard(["Москва"])
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons[0] == "✅ Москва"
    assert buttons[1] == "⬜ Санкт-Петербург"


def test_regions_keyboard_bulk_actions_below_list():
    kb = regions_keyboard([])
    rows = kb.inline_keyboard
    bulk = rows[len(ALL_REGION_KEYS)]
    assert [btn.text for btn in bulk] == ["✔️ Выбрать все", "🗑️ Сбросить"]
    assert [btn.callback_data for btn in bulk] == ["region:all:", "region:clear:"]
    back_row = rows[len(ALL_REGION_KEYS) + 1]
    assert back_row[0].callback_data == "region:back:"