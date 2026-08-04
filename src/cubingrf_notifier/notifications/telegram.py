from aiogram import Bot

from ..config import settings
from ..database.models import Competition


class TelegramNotifier:
    def __init__(self, token: str | None = None):
        token = token or settings.telegram_token
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN not provided in settings")
        self.bot = Bot(token=token)

    @staticmethod
    def _format_competition(comp: Competition) -> str:
        return (
            "🧊 Новое соревнование!\n\n"
            f"Название:\n{comp.name}\n\n"
            f"Дата:\n{comp.date.strftime('%d.%m.%Y') if comp.date else 'не указана'}\n\n"
            f"Место:\n{comp.location or 'не указано'}\n\n"
            f"Подробнее:\n{comp.url or '—'}"
        )

    async def send_competition(self, chat_id: int, comp: Competition) -> None:
        await self.bot.send_message(chat_id, self._format_competition(comp))

    async def close(self) -> None:
        await self.bot.session.close()
