from types import SimpleNamespace
from unittest.mock import patch

import pytest

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import UserRepository
from cubingrf_notifier.bot.middleware import SyncUsernameMiddleware


@pytest.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


def _from_user(user_id=111, username="alex"):
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id, username=username))


async def _run(mw, event):
    calls = []

    async def handler(ev, data):
        calls.append(ev)
        return "ok"

    result = await mw(handler, event, {})
    return calls, result


async def _get_user(maker, telegram_id):
    async with maker() as sess:
        return await UserRepository(sess).get_user_by_telegram_id(telegram_id)


# --- no-op cases ---

async def test_middleware_passthrough_without_from_user(session_maker):
    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        calls, result = await _run(mw, SimpleNamespace())
    assert len(calls) == 1
    assert result == "ok"


async def test_middleware_noop_when_no_username(session_maker):
    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(username=None))
    assert await _get_user(session_maker, 111) is None


# --- username persistence ---

async def test_middleware_updates_existing_user(session_maker):
    async with session_maker() as sess:
        await UserRepository(sess).create_user(111)
        await sess.commit()

    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(111, "alex"))

    user = await _get_user(session_maker, 111)
    assert user.username == "alex"


async def test_middleware_does_not_create_unknown_user(session_maker):
    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(999, "alex"))

    user = await _get_user(session_maker, 999)
    assert user is None


async def test_middleware_preserves_language(session_maker):
    async with session_maker() as sess:
        await UserRepository(sess).register_user(111, "alex", "en")
        await UserRepository(sess).set_user_language(111, "ru")
        await sess.commit()

    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(111, "new_name"))

    user = await _get_user(session_maker, 111)
    assert user.username == "new_name"
    assert user.language == "ru"


# --- last_seen_at (activity tracking) ---

async def test_middleware_updates_last_seen_at(session_maker):
    async with session_maker() as sess:
        await UserRepository(sess).register_user(111, "alex", "en")
        await sess.commit()

    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(111, "alex"))

    user = await _get_user(session_maker, 111)
    assert user.last_seen_at is not None


async def test_middleware_updates_last_seen_at_without_username(session_maker):
    async with session_maker() as sess:
        await UserRepository(sess).register_user(111, None, "en")
        await sess.commit()

    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(111, None))

    user = await _get_user(session_maker, 111)
    assert user.last_seen_at is not None
    assert user.username is None


async def test_middleware_reactivates_blocked_user(session_maker):
    async with session_maker() as sess:
        await UserRepository(sess).register_user(111, "alex", "en")
        await UserRepository(sess).set_blocked(111)
        await sess.commit()

    mw = SyncUsernameMiddleware()
    with patch("cubingrf_notifier.bot.middleware.AsyncSessionLocal", session_maker):
        await _run(mw, _from_user(111, "alex"))

    user = await _get_user(session_maker, 111)
    assert user.blocked_at is None
    assert user.last_seen_at is not None