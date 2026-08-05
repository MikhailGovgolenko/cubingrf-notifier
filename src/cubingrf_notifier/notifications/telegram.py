from aiogram import Bot

from ..config import settings
from ..database.models import Competition
from .competition_formatter import format_competition_notification


class TelegramNotifier:
    def __init__(self, token: str | None = None):
        token = token or settings.telegram_token
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN not provided in settings")
        self.bot = Bot(token=token)

    async def send_competition(
        self,
        chat_id: int,
        comp: Competition,
        language: str = "ru",
    ) -> None:
        text = format_competition_notification(comp, language)
        await self.bot.send_message(chat_id, text)

    async def close(self) -> None:
        await self.bot.session.close()
