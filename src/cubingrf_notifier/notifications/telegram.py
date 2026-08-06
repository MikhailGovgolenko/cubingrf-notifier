from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..config import settings
from ..database.models import Competition
from .competition_formatter import format_competition_notification, format_registration_reminder


class TelegramNotifier:
    def __init__(self, token: str | None = None):
        token = token or settings.telegram_token
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN not provided in settings")
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def send_competition(
        self,
        chat_id: int,
        comp: Competition,
        language: str = "ru",
        kind: str = "new",
    ) -> None:
        if kind == "reg_soon":
            text = format_registration_reminder(comp, language)
        else:
            text = format_competition_notification(comp, language)
        await self.bot.send_message(chat_id, text)

    async def close(self) -> None:
        await self.bot.session.close()
