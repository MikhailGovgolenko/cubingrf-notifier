from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    database_url: str
    telegram_token: str | None = None
    poll_interval: int = 300
    # Fast cadence (seconds) for the round-result poller.
    results_poll_interval: int = 60

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = AppSettings()  # pyright: ignore[reportCallIssue]