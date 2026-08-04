cubingrf-notifier
=================

Telegram notifier for CubingRF competitions.

Бот автоматически отслеживает новые соревнования по спидкубингу на сайте
cubingrf.org и уведомляет подписанных пользователей.

## Запуск

Предварительно скопируйте `.env.example` в `.env` и заполните `TELEGRAM_TOKEN`:

```bash
cp .env.example .env
```

Запуск (построит образ, поднимет PostgreSQL, применит миграции и запустит бота):

```bash
docker compose up --build
```

Остановка:

```bash
docker compose down
```

Логи:

```bash
docker compose logs -f web
```

## Команды бота

- `/start` — подписаться на уведомления
- `/stop` — отписаться от уведомлений
- `/status` — статус подписки
- `/settings` — настройки (меню)
- `/competitions` — ближайшие соревнования
- `/help` — список команд

## Project layout

```
src/cubingrf_notifier — main package
```

- `config.py` — настройки через pydantic-settings (`.env`)
- `bot/` — Telegram-хендлеры и клавиатуры (aiogram 3)
- `database/` — SQLAlchemy async модели, сессия, репозитории
- `competitions/` — бизнес-логика и DTO соревнований
- `scrapers/` — парсер cubingrf.org
- `notifications/` — отправка сообщений в Telegram
- `scheduler/` — APScheduler
- `alembic/` — миграции БД

## База данных

Миграции применяются автоматически при старте контейнера (`alembic upgrade head`).

Локально:

```bash
alembic upgrade head
```
