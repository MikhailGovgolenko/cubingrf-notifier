import asyncio
import logging

from .config import settings

from .scrapers.cubingrf_html import CubingRFHtmlScraper
from .competitions.service import CompetitionService

from .database.session import AsyncSessionLocal
from .database.repository import (
    UserRepository,
    NotificationRepository,
)

from .scheduler.jobs import (
    create_scheduler,
    run_scheduler,
)

from .notifications.telegram import TelegramNotifier

from .bot.bot import dp, bot


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def check_and_notify():

    async with AsyncSessionLocal() as sess:

        source = CubingRFHtmlScraper()

        service = CompetitionService(
            source,
            sess
        )

        new = await service.check_new_competitions()


        if not new:
            logger.info(
                "No new competitions"
            )

            await sess.commit()
            return


        notifier = TelegramNotifier()


        user_repo = UserRepository(sess)

        notif_repo = NotificationRepository(sess)


        users = await user_repo.list_users()


        for comp in new:

            for user in users:

                try:

                    await notifier.send_competition(
                        user.telegram_id,
                        comp.__dict__
                    )


                    await notif_repo.mark_sent(
                        user.id,
                        0
                    )


                except Exception:

                    logger.exception(
                        "Failed to notify user %s",
                        user.telegram_id
                    )


        await sess.commit()

        await notifier.close()



async def main():

    if bot is None:

        raise RuntimeError(
            "Telegram bot token is not configured. "
            "Set TELEGRAM_TOKEN in .env"
        )


    scheduler = create_scheduler(
        check_and_notify,
        settings.poll_interval
    )


    loop = asyncio.get_running_loop()


    loop.create_task(
        run_scheduler(scheduler)
    )


    try:

        await dp.start_polling(
            bot
        )


    finally:

        await bot.session.close()



if __name__ == "__main__":

    asyncio.run(main())