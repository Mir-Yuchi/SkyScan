from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.
    """

    app_name: str = "SkyScan"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    database_url: PostgresDsn


settings = Settings()
