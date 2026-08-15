from aiogram import Bot
from aiogram.types import InputRichMessage

from ..config import settings
from ..database.models import Competition
from .competition_formatter import format_competition_notification, format_registration_reminder
from ..results.formatter import format_round_result
from ..results.models import RoundSnapshot


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
        kind: str = "new",
        countdown_at=None,
    ) -> None:
        if kind == "reg_soon":
            text = format_registration_reminder(comp, language, countdown_at=countdown_at)
        else:
            text = format_competition_notification(comp, language)
        await self.bot.send_rich_message(
            chat_id, rich_message=InputRichMessage(html=text)
        )

    async def send_round_result(
        self,
        chat_id: int,
        *,
        competition_name: str,
        competition_url: str | None,
        event_code: str,
        round_number: int,
        snapshot: RoundSnapshot,
        language: str = "ru",
        edited: bool = False,
    ) -> None:
        text = format_round_result(
            competition_name,
            competition_url,
            event_code,
            round_number,
            snapshot,
            language,
            edited=edited,
        )
        await self.bot.send_rich_message(
            chat_id, rich_message=InputRichMessage(html=text)
        )

    async def close(self) -> None:
        await self.bot.session.close()
