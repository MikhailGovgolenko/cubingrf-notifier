from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from ..config import settings
from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository, CompetitionRepository

bot = Bot(token=settings.telegram_token) if settings.telegram_token else None
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Register user in DB."""
    if not settings.telegram_token:
        await message.answer("Bot token not configured")
        return
    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        await user_repo.create_user(message.from_user.id)
        await sess.commit()
    await message.answer("Вы успешно подписаны на уведомления")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("/start - подписаться\n/competitions - показать ближайшие соревнования")

@dp.message(Command("competitions"))
async def cmd_competitions(message: Message):
    async with AsyncSessionLocal() as sess:
        comp_repo = CompetitionRepository(sess)
        comps = await comp_repo.get_latest_competitions()
    if not comps:
        await message.answer("Пока нет найденных соревнований")
        return
    text = "Ближайшие соревнования:\n\n"
    for c in comps:
        date_str = c.date.isoformat() if c.date else '-'
        text += f"{c.name} — {date_str} — {c.location or '-'}\n{c.url or ''}\n\n"
    await message.answer(text)
