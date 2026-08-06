import logging

from aiogram import BaseMiddleware

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository

logger = logging.getLogger(__name__)


class SyncUsernameMiddleware(BaseMiddleware):
    """Tracks activity and refreshes ``users.username`` on every interaction.

    Runs for each message, callback query and command. For an already-registered
    user it refreshes ``username`` (only when a new value arrived; the chosen
    language is never touched), stamps ``last_seen_at`` with the current time,
    and clears ``blocked_at`` so a previously blocked user is active again. It
    never creates users: unknown Telegram accounts are left untouched so the
    activity tracking applies only to registered users.
    """

    async def __call__(self, handler, event, data):
        from_user = getattr(event, "from_user", None)
        if from_user is not None:
            await self._track_activity(from_user.id, getattr(from_user, "username", None))
        return await handler(event, data)

    async def _track_activity(self, telegram_id: int, username) -> None:
        try:
            async with AsyncSessionLocal() as sess:
                if await UserRepository(sess).mark_seen(telegram_id, username):
                    await sess.commit()
        except Exception:
            logger.exception("Failed to track activity for user %s", telegram_id)