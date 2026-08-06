import pytest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import UserRepository
from cubingrf_notifier.competitions.disciplines import ALL_DISCIPLINE_CODES, DISCIPLINES
from cubingrf_notifier.competitions.regions import ALL_REGION_KEYS
from cubingrf_notifier.bot.events import (
    cb_toggle,
    cb_select_all,
    cb_clear,
    cb_events_back,
)
from cubingrf_notifier.bot.regions import (
    cb_region_toggle,
    cb_region_select_all,
    cb_region_clear,
    cb_regions_back,
)
from cubingrf_notifier.bot.keyboards import EventCB, RegionCB
from cubingrf_notifier.i18n import get_text


@pytest.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


class _FakeMessage:
    def __init__(self):
        self.text = None
        self.reply_markup = None

    async def edit_text(self, text, reply_markup=None):
        self.text = text
        self.reply_markup = reply_markup


class _FakeCallback:
    def __init__(self, user_id):
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()

    async def answer(self, **kwargs):
        pass


async def _create_user(maker, user_id):
    async with maker() as sess:
        await UserRepository(sess).create_user(user_id)
        await sess.commit()


def _buttons(rows):
    return [btn.text for row in rows for btn in row]


# --- disciplines: actions keep the user on the picker screen ---

async def test_discipline_toggle_stays_on_picker(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code="333"))
    assert cb.message.text.startswith(get_text("ru", "disciplines.title"))
    assert get_text("ru", "settings.title") not in cb.message.text
    rows = cb.message.reply_markup.inline_keyboard
    assert rows[0][0].text == "✅ 3x3x3"
    assert rows[1][0].text == "⬜ 2x2x2"


async def test_discipline_toggle_off_stays_on_picker(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code="333"))
        await cb_toggle(cb, EventCB(action="toggle", code="333"))
    rows = cb.message.reply_markup.inline_keyboard
    assert rows[0][0].text == "⬜ 3x3x3"
    assert get_text("ru", "settings.title") not in cb.message.text


async def test_discipline_select_all_stays_on_picker(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_select_all(cb)
    assert cb.message.text.startswith(get_text("ru", "disciplines.title"))
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("✅ ") for t in _buttons(rows[: len(DISCIPLINES)]))


async def test_discipline_clear_stays_on_picker(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code="333"))
        await cb_clear(cb)
    assert cb.message.text.startswith(get_text("ru", "disciplines.title"))
    assert get_text("ru", "disciplines.none") in cb.message.text
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("⬜ ") for t in _buttons(rows[: len(DISCIPLINES)]))


async def test_discipline_back_returns_to_settings(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.user_status.AsyncSessionLocal", session_maker):
        await cb_events_back(cb)
    assert cb.message.text.count(get_text("ru", "settings.title")) > 0


# --- regions: actions keep the user on the picker screen ---

async def test_region_toggle_stays_on_picker(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key="Москва"))
    assert cb.message.text.startswith(get_text("ru", "regions.title"))
    assert get_text("ru", "settings.title") not in cb.message.text
    rows = cb.message.reply_markup.inline_keyboard
    assert rows[0][0].text == "✅ Москва"
    assert rows[1][0].text == "⬜ Московская область"


async def test_region_select_all_stays_on_picker(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_select_all(cb)
    assert cb.message.text.startswith(get_text("ru", "regions.title"))
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("✅ ") for t in _buttons(rows[: len(ALL_REGION_KEYS)]))


async def test_region_clear_stays_on_picker(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key="Москва"))
        await cb_region_clear(cb)
    assert cb.message.text.startswith(get_text("ru", "regions.title"))
    assert get_text("ru", "regions.none") in cb.message.text
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("⬜ ") for t in _buttons(rows[: len(ALL_REGION_KEYS)]))


async def test_region_back_returns_to_settings(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.user_status.AsyncSessionLocal", session_maker):
        await cb_regions_back(cb)
    assert cb.message.text.count(get_text("ru", "settings.title")) > 0
