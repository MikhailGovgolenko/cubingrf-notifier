from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ...database.session import AsyncSessionLocal
from ...database.repository import UserRepository


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)

        user = await user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            await user_repo.create(
                telegram_id=telegram_id
            )

    await message.answer(
        "👋 Привет!\n\n"
        "Я CubingRF Notifier.\n"
        "Буду уведомлять тебя о новых соревнованиях по спидкубингу.\n\n"
        "Команды:\n"
        "/start — начать\n"
        "/help — помощь"
    )