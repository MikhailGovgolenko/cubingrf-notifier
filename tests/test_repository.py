import pytest

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from cubingrf_notifier.database.models import Base
from cubingrf_notifier.database.repository import UserRepository
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