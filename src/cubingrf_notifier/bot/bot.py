from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from ..config import settings
from ..database import session as db_session
from ..database.session import AsyncSessionLocal
from ..database.repository import Repository

bot = Bot(token=settings.telegram_token) if settings.telegram_token else None
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Register user in DB."""
    if not settings.telegram_token:
        await message.answer("Bot token not configured")
        return
    async with AsyncSessionLocal() as sess:
        repo = Repository(sess)
        user = await repo.add_user_if_not_exists(message.from_user.id)
        await sess.commit()
    await message.answer("Вы успешно подписаны на уведомления")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("/start - подписаться\n/competitions - показать ближайшие соревнования")

@dp.message(Command("competitions"))
async def cmd_competitions(message: Message):
    async with AsyncSessionLocal() as sess:
        repo = Repository(sess)
        comps = await repo.get_upcoming_competitions()
    if not comps:
        await message.answer("Пока нет найденных соревнований")
        return
    text = "Ближайшие соревнования:\n\n"
    for c in comps:
        text += f"{c.name} — {c.date or '-'} — {c.location or '-'}\n{c.url or ''}\n\n"
    await message.answer(text)
