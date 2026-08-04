#!/bin/sh
set -e

echo "Waiting for database..."

python - <<'PY'
import asyncio
import asyncpg
import os

async def main():
    url = os.environ["DATABASE_URL"]
    url = url.replace("postgresql+asyncpg://", "postgresql://")

    while True:
        try:
            conn = await asyncpg.connect(url)
            await conn.close()
            break
        except Exception:
            print("Database not ready, waiting...")
            await asyncio.sleep(2)

asyncio.run(main())
PY


echo "Running database migrations..."

alembic upgrade head


echo "Starting bot..."

exec python -m cubingrf_notifier.main