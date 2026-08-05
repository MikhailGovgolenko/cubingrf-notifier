import logging

from aiogram import BaseMiddleware

from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository

logger = logging.getLogger(__name__)


class SyncUsernameMiddleware(BaseMiddleware):
    """Refresh ``users.username`` from every incoming interaction.

    Runs for each message and callback query. Only updates the username of an
    already-registered user and never the chosen language: language is set at
    first registration only. A no-op when Telegram sent no username or when the
    value did not change, so no UPDATE is issued.
    """

    async def __call__(self, handler, event, data):
        from_user = getattr(event, "from_user", None)
        if from_user is not None:
            await self._sync_username(from_user.id, getattr(from_user, "username", None))
        return await handler(event, data)

    async def _sync_username(self, telegram_id: int, username) -> None:
        if not username:
            return
        try:
            async with AsyncSessionLocal() as sess:
                if await UserRepository(sess).sync_username(telegram_id, username):
                    await sess.commit()
        except Exception:
            logger.exception("Failed to sync username for user %s", telegram_id)