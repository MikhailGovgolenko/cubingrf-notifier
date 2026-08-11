import asyncio
import logging
import signal

from .config import settings

from .scrapers.cubingrf_html import CubingRFHtmlScraper
from .competitions.service import CompetitionService

from aiogram.exceptions import TelegramForbiddenError

from .database.session import AsyncSessionLocal, engine
from .database.repository import (
    UserRepository,
    NotificationRepository,
)

from .scheduler.jobs import create_scheduler

from .notifications.telegram import TelegramNotifier
from .notifications.matcher import should_notify_user
from .notifications.reg_reminder import reconcile_registration_reminders

from .results.service import RoundResultService

from .bot.bot import dp, bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)


async def check_and_notify() -> None:
    """Fetch new competitions, notify users, and fire registration reminders."""
    async with AsyncSessionLocal() as sess:
        service = CompetitionService(CubingRFHtmlScraper(), sess)
        new = await service.check_new_competitions()

        if new:
            logger.info("New competitions found: %d", len(new))

            notifier = TelegramNotifier()
            user_repo = UserRepository(sess)
            notif_repo = NotificationRepository(sess)

            users = await user_repo.list_enabled_users()
            if users:
                # Preload each user's region/event preferences for filtering.
                user_regions = {
                    u.telegram_id: await user_repo.get_user_regions(u.telegram_id)
                    for u in users
                }
                user_events = {
                    u.telegram_id: await user_repo.get_user_events(u.telegram_id)
                    for u in users
                }

                for comp in new:
                    for user in users:
                        try:
                            if not should_notify_user(
                                user,
                                comp,
                                user_region_keys=user_regions[user.telegram_id],
                                user_event_codes=user_events[user.telegram_id],
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
                        except TelegramForbiddenError:
                            logger.warning(
                                "User cannot be reached (blocked bot), marking as blocked telegram_id=%s",
                                user.telegram_id,
                            )
                            await user_repo.set_blocked(user.telegram_id)
                        except Exception:
                            logger.exception(
                                "Failed to notify user competition=%s telegram_id=%s",
                                comp.id,
                                user.telegram_id,
                            )
            else:
                logger.info("No subscribed users; competitions stored, nothing to notify")

            await sess.commit()
            await notifier.close()
        else:
            await sess.commit()
            logger.info("No new competitions")


async def poll_round_results() -> None:
    """Fast job: poll user round results and notify on completion/edits."""
    async with AsyncSessionLocal() as sess:
        service = RoundResultService(sess)
        try:
            result = await service.poll()
            if result:
                logger.info("Round-result poll events: %s", result)
        except Exception:
            logger.exception("Round-result poll failed")
        finally:
            await sess.close()


async def main() -> None:
    if bot is None:
        raise RuntimeError(
            "Telegram bot token is not configured. Set TELEGRAM_TOKEN in .env"
        )

    scheduler = create_scheduler(
        check_and_notify,
        settings.poll_interval,
        reminder_reconciler=reconcile_registration_reminders,
        results_poll_job=poll_round_results,
        results_poll_interval=settings.results_poll_interval,
    )
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
