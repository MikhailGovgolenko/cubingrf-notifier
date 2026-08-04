from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

from ..config import settings
from ..database.session import AsyncSessionLocal
from ..database.repository import UserRepository, CompetitionRepository
from .settings import router as settings_router


bot = Bot(token=settings.telegram_token) if settings.telegram_token else None

dp = Dispatcher()
dp.include_router(settings_router)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Register the user and enable notifications.

    New users get a welcome message; existing users are just re-enabled
    without creating a duplicate row.
    """
    user = message.from_user
    if user is None:
        return

    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        existing = await user_repo.get_user_by_telegram_id(user.id)

        if existing is None:
            await user_repo.create_user(user.id)
            await sess.commit()
            await message.answer(
                "🧊 CubingRF Notifier\n"
                "Бот автоматически уведомляет о новых соревнованиях WCA в России.\n\n"
                "Команды:\n"
                "/competitions — ближайшие соревнования\n"
                "/status — настройки подписки\n"
                "/settings — настройки\n"
                "/stop — отключить уведомления"
            )
            return

        await user_repo.set_notifications_enabled(user.id, True)
        await sess.commit()

    await message.answer("Вы снова подписались на уведомления.")


@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    """Unsubscribe the user from notifications."""
    user = message.from_user
    if user is None:
        return

    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        updated = await user_repo.set_notifications_enabled(user.id, False)
        await sess.commit()

    if updated is None:
        await message.answer("Вы ещё не подписаны. Отправьте /start, чтобы подписаться.")
        return

    await message.answer("Вы отписаны от уведомлений. Для повторной подписки — /start.")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Show the user's subscription status."""
    user = message.from_user
    if user is None:
        return

    async with AsyncSessionLocal() as sess:
        user_repo = UserRepository(sess)
        db_user = await user_repo.get_user_by_telegram_id(user.id)

    if db_user is None:
        await message.answer("Вы не подписаны на уведомления. Отправьте /start.")
        return

    notifications = "включены ✅" if db_user.notifications_enabled else "выключены ❌"
    await message.answer(
        "📢 Статус подписки\n\n"
        f"Уведомления: {notifications}\n\n"
        "Настройки:\n"
        "Регион: все\n"
        "Дисциплины: все"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Помощь\n\n"
        "/start — подписаться на уведомления\n"
        "/stop — отписаться от уведомлений\n"
        "/status — статус подписки\n"
        "/settings — настройки\n"
        "/competitions — показать ближайшие соревнования\n"
        "/help — список команд"
    )


@dp.message(Command("competitions"))
async def cmd_competitions(message: Message):
    async with AsyncSessionLocal() as sess:
        comp_repo = CompetitionRepository(sess)
        comps = await comp_repo.get_upcoming_competitions()

    if not comps:
        await message.answer("Пока нет найденных соревнований.")
        return

    text = "🏆 Ближайшие соревнования:\n\n"

    for c in comps:
        date = c.date.strftime("%d.%m.%Y") if c.date else "дата неизвестна"
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
