# cubingrf-notifier

<p align="center">
  <img src="assets/logo.svg" alt="cubingrf-notifier logo" width="220">
</p>

Telegram-бот, который автоматически отслеживает новые соревнования на
[cubingrf.org](https://cubingrf.org) и уведомляет подписанных пользователей.

## Возможности

- 🔔 Уведомления о новых соревнованиях
- ⏰ Напоминания об открытии регистрации
- 🌍 Фильтрация по регионам
- 🏆 Просмотр ближайших соревнований
- ⚙️ Настройка уведомлений прямо в Telegram

## Запуск

Сначала скопируйте файл с примером настроек:

```bash
cp .env.example .env
```

Заполните в `.env` как минимум:

```text
TELEGRAM_TOKEN=...
```

Запуск проекта:

```bash
docker compose up --build
```

Эта команда:

- собирает Docker-образ;
- запускает PostgreSQL;
- применяет миграции (`alembic upgrade head`);
- запускает Telegram-бота.

Остановка:

```bash
docker compose down
```

Просмотр логов:

```bash
docker compose logs -f web
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Подписаться на уведомления |
| `/stop` | Отписаться от уведомлений |
| `/status` | Проверить статус подписки |
| `/settings` | Открыть настройки |
| `/competitions` | Показать ближайшие соревнования |
| `/help` | Список команд |

## Структура проекта

```
src/cubingrf_notifier
├── bot/              # Telegram-бот (aiogram 3)
├── competitions/     # Бизнес-логика соревнований
├── database/         # SQLAlchemy, модели и репозитории
├── notifications/    # Формирование и отправка уведомлений
├── scheduler/        # APScheduler
├── scrapers/         # Парсер cubingrf.org
├── alembic/          # Миграции базы данных
└── config.py         # Настройки приложения
```

## База данных

При запуске через Docker миграции применяются автоматически:

```bash
alembic upgrade head
```

При необходимости их можно выполнить вручную:

```bash
alembic upgrade head
```
