FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip && pip install -e .

CMD ["python", "-m", "cubingrf_notifier.main"]
