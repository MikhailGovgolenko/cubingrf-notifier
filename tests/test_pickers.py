import pytest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import UserRepository
from cubingrf_notifier.competitions.disciplines import DISCIPLINES
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

    async def edit_text(self, text=None, rich_message=None, reply_markup=None):
        self.text = rich_message.html if rich_message is not None else text
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
    assert cb.message.text.startswith("<h1>" + get_text("ru", "disciplines.title") + "</h1>")
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
    assert cb.message.text.startswith("<h1>" + get_text("ru", "disciplines.title") + "</h1>")
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("✅ ") for t in _buttons(rows[: len(DISCIPLINES)]))


async def test_discipline_clear_stays_on_picker(session_maker):
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code="333"))
        await cb_clear(cb)
    assert cb.message.text.startswith("<h1>" + get_text("ru", "disciplines.title") + "</h1>")
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


async def test_discipline_toggle_rejects_oversized_forged_code(session_maker):
    """Forged callback data with a code longer than the column must be ignored."""
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    forged = "x" * 64  # exceeds String(20)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code=forged))
    # Rejected before persisting/rendering: the picker is not re-rendered.
    assert cb.message.reply_markup is None


async def test_discipline_toggle_accepts_unknown_short_code(session_maker):
    """Unknown-but-valid-length codes stay allowed (future events can appear)."""
    user_id = 111
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.events.AsyncSessionLocal", session_maker):
        await cb_toggle(cb, EventCB(action="toggle", code="999new"))
    assert "999new" in cb.message.text


async def test_region_toggle_rejects_oversized_forged_key(session_maker):
    """Forged callback data with a key longer than the column must be ignored."""
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    forged = "y" * 256  # exceeds String(128)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key=forged))
    # Rejected before persisting/rendering: the picker is not re-rendered.
    assert cb.message.reply_markup is None


async def test_region_selection_escapes_html(session_maker):
    """User-selected region keys are HTML-escaped on render (self-XSS guard)."""
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key="<script>alert(1)</script>"))
    assert "<script>" not in cb.message.text
    assert "&lt;script&gt;" in cb.message.text


# --- RSF id: oversized input is capped at the column limit ---

class _FakeState:
    def __init__(self):
        self.cleared = False

    async def clear(self):
        self.cleared = True


class _RsfMessage:
    def __init__(self, user_id, text):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.rendered = None

    async def answer_rich(self, rich_message, reply_markup=None):
        self.rendered = rich_message.html


async def test_rsf_id_is_capped_to_column_limit(session_maker):
    from cubingrf_notifier.bot.notify_settings import msg_set_rsf

    user_id = 333
    await _create_user(session_maker, user_id)
    state = _FakeState()
    msg = _RsfMessage(user_id, "A" * 100)
    with patch("cubingrf_notifier.bot.notify_settings.AsyncSessionLocal", session_maker):
        await msg_set_rsf(msg, state)
    assert state.cleared
    async with session_maker() as sess:
        stored = await UserRepository(sess).get_rsf_id(user_id)
    assert stored == "A" * 32
    assert stored is not None and len(stored) <= 32


# --- regions: actions keep the user on the picker screen ---

async def test_region_toggle_stays_on_picker(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key="Москва"))
    assert cb.message.text.startswith("<h1>" + get_text("ru", "regions.title") + "</h1>")
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
    assert cb.message.text.startswith("<h1>" + get_text("ru", "regions.title") + "</h1>")
    rows = cb.message.reply_markup.inline_keyboard
    assert all(t.startswith("✅ ") for t in _buttons(rows[: len(ALL_REGION_KEYS)]))


async def test_region_clear_stays_on_picker(session_maker):
    user_id = 222
    await _create_user(session_maker, user_id)
    cb = _FakeCallback(user_id)
    with patch("cubingrf_notifier.bot.regions.AsyncSessionLocal", session_maker):
        await cb_region_toggle(cb, RegionCB(action="toggle", key="Москва"))
        await cb_region_clear(cb)
    assert cb.message.text.startswith("<h1>" + get_text("ru", "regions.title") + "</h1>")
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
