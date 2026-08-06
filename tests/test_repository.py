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