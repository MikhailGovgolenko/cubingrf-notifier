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
    """
    Register user in database.
    """

    if not message.from_user:
        return

    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)

        await user_repo.create_user(
            telegram_id=message.from_user.id
        )

        await sess.commit()

    await message.answer(
        "👋 Добро пожаловать в CubingRF Notifier!\n\n"
        "Вы успешно подписаны на уведомления о новых соревнованиях.\n\n"
        "Команды:\n"
        "/competitions — ближайшие соревнования\n"
        "/help — помощь"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Помощь\n\n"
        "/start — подписаться на уведомления\n"
        "/competitions — показать соревнования\n"
        "/help — список команд"
    )


@dp.message(Command("competitions"))
async def cmd_competitions(message: Message):

    async with AsyncSessionLocal() as sess:
        comp_repo = CompetitionRepository(sess)

        comps = await comp_repo.get_latest_competitions()

    if not comps:
        await message.answer(
            "Пока нет найденных соревнований."
        )
        return


    text = "🏆 Ближайшие соревнования:\n\n"

    for c in comps:
        date = (
            c.date.isoformat()
            if c.date
            else "дата неизвестна"
        )

        location = c.location or "-"

        text += (
            f"🔹 {c.name}\n"
            f"📅 {date}\n"
            f"📍 {location}\n"
        )

        if c.url:
            text += f"🔗 {c.url}\n"

        text += "\n"


    await message.answer(text)
