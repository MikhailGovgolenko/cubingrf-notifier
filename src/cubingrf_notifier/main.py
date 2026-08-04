import asyncio
import logging
from .config import settings
from .scrapers.cubingrf_html import CubingRFHtmlScraper
from .competitions.service import CompetitionService
from .database.session import AsyncSessionLocal, engine
from .scheduler.jobs import create_scheduler, run_scheduler
from .notifications.telegram import TelegramNotifier
from .bot.bot import dp, bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_and_notify():
    async with AsyncSessionLocal() as sess:
        source = CubingRFHtmlScraper()
        service = CompetitionService(source, sess)
        new = await service.check_new_competitions()
        if not new:
            logger.info("No new competitions")
            await sess.commit()
            return
        notifier = TelegramNotifier()
        # get users
        from .database.repository import Repository
        repo = Repository(sess)
        users = await repo.get_subscribed_users()
        for comp in new:
            for u in users:
                try:
                    await notifier.send_competition(u.telegram_id, comp.__dict__)
                    await repo.add_notification(u.id, 0)
                except Exception:
                    logger.exception("Failed to notify user %s", u.telegram_id)
        await sess.commit()
        await notifier.close()

async def main():
    # create scheduler
    scheduler = create_scheduler(check_and_notify, settings.poll_interval)
    # run scheduler and bot
    loop = asyncio.get_event_loop()
    # Start scheduler in background task
    loop.create_task(run_scheduler(scheduler))
    # Start aiogram polling
    try:
        from aiogram import Dispatcher
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
