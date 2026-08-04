cubingrf-notifier
=================

Telegram notifier for CubingRF competitions.

Quickstart:
1. Copy .env.example -> .env and fill DATABASE_URL and TELEGRAM_TOKEN
2. docker compose up -d (runs postgres)
3. Build and run the app (or run locally with Python)

Project layout: src/cubingrf_notifier — main package.

## Database setup

1. Start Postgres (example using docker-compose):

   docker compose up -d db

2. Create .env with DATABASE_URL and other vars (see .env.example)

3. Run migrations:

   alembic upgrade head


Note: Alembic configuration picks up DATABASE_URL from src/cubingrf_notifier/config.py via pydantic-settings. Ensure .env is present when running alembic.

