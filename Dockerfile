FROM python:3.13-slim

# uv is pinned to a specific release for reproducible tooling. It installs the
# exact versions recorded in uv.lock (--frozen), so the image does not float.
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy dependency manifests first so a source-only change reuses the cached
# dependency layer.
COPY pyproject.toml uv.lock ./
COPY src ./src

COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./

# Install exact pinned versions from uv.lock (no upgrade, no floating bounds).
RUN uv sync --frozen --no-dev

RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

# Run as an unprivileged user: the app only reads source and talks to the DB,
# so root privileges are unnecessary at runtime.
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]