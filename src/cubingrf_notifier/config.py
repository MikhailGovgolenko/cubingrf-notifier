try:
    from pydantic_settings import BaseSettings
    from typing import Optional

    class Settings(BaseSettings):
        database_url: str
        telegram_token: Optional[str] = None
        poll_interval: int = 300

        class Config:
            env_file = ".env"

    settings = Settings()
except Exception:  # pragma: no cover - fallback when pydantic not installed
    class Settings:
        database_url = "sqlite+aiosqlite:///./test.db"
        telegram_token = None
        poll_interval = 300

    settings = Settings()
