FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./

RUN pip install --upgrade pip && pip install -e .

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]