from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    telegram_token: Optional[str] = None
    poll_interval: int = 300

    class Config:
        env_file = ".env"

settings = Settings()
