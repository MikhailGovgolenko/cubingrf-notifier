import asyncio
import logging
import signal

from .config import settings

from .scrapers.cubingrf_html import CubingRFHtmlScraper
from .competitions.service import CompetitionService

from .database.session import AsyncSessionLocal, engine
from .database.repository import (
    UserRepository,
    NotificationRepository,
)

from .scheduler.jobs import create_scheduler

from .notifications.telegram import TelegramNotifier
from .notifications.matcher import should_notify_user

from .bot.bot import dp, bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)


async def check_and_notify() -> None:
    """Fetch new competitions and notify all subscribed users."""
    async with AsyncSessionLocal() as sess:
        service = CompetitionService(CubingRFHtmlScraper(), sess)
        new = await service.check_new_competitions()

        if not new:
            await sess.commit()
            logger.info("No new competitions")
            return

        logger.info("New competitions found: %d", len(new))

        notifier = TelegramNotifier()
        user_repo = UserRepository(sess)
        notif_repo = NotificationRepository(sess)

        users = await user_repo.list_enabled_users()
        if not users:
            logger.info("No subscribed users; competitions stored, nothing to notify")
            await sess.commit()
            await notifier.close()
            return

        # Preload each user's region/discipline preferences for filtering.
        user_regions = {
            u.telegram_id: await user_repo.get_user_regions(u.telegram_id)
            for u in users
        }
        user_disciplines = {
            u.telegram_id: await user_repo.get_user_disciplines(u.telegram_id)
            for u in users
        }

        for comp in new:
            for user in users:
                try:
                    if not should_notify_user(
                        user,
                        comp,
                        user_region_keys=user_regions[user.telegram_id],
                        user_discipline_codes=user_disciplines[user.telegram_id],
                    ):
                        continue
                    logger.info(
                        "Sending notification competition=%s user=%s",
                        comp.id,
                        user.telegram_id,
                    )
                    await notifier.send_competition(
                        user.telegram_id,
                        comp,
                        language=user.language or "ru",
                    )
                    await notif_repo.mark_sent(user.id, comp.id)
                    logger.info(
                        "Notification sent competition=%s user=%s",
                        comp.id,
                        user.telegram_id,
                    )
                except Exception:
                    logger.exception(
                        "Failed to notify user competition=%s telegram_id=%s",
                        comp.id,
                        user.telegram_id,
                    )

        await sess.commit()
        await notifier.close()


async def main() -> None:
    if bot is None:
        raise RuntimeError(
            "Telegram bot token is not configured. Set TELEGRAM_TOKEN in .env"
        )

    scheduler = create_scheduler(check_and_notify, settings.poll_interval)
    scheduler.start()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(scheduler)))
        except NotImplementedError:
            # e.g. Windows does not support add_signal_handler for some signals.
            logger.warning("Signal handler for %s is not supported", sig)

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await engine.dispose()
        logger.info("Shutdown complete")


async def shutdown(scheduler) -> None:
    """Request graceful shutdown of the polling loop."""
    logger.info("Stop signal received, stopping polling...")
    await dp.stop_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted, exiting")
