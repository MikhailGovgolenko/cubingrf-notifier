from aiogram import Bot
from typing import List
from ..config import settings

class TelegramNotifier:
    def __init__(self, token: str | None = None):
        token = token or settings.telegram_token
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN not provided in settings")
        self.bot = Bot(token=token)

    async def send_competition(self, chat_id: int, competition: dict):
        text = (
            "🆕 Новое соревнование CubingRF\n\n"
            f"🏆 Название: {competition.get('name')}\n"
            f"📍 Место: {competition.get('location') or '—'}\n"
            f"📅 Дата: {competition.get('date') or '—'}\n"
            f"🧩 Дисциплины: {', '.join(competition.get('disciplines') or [])}\n"
            f"🔗 Ссылка: {competition.get('url') or '—'}"
        )
        await self.bot.send_message(chat_id, text)

    async def close(self):
        await self.bot.session.close()
