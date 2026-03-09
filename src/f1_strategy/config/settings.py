from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="f1_strategy", alias="POSTGRES_DB")
    postgres_user: str = Field(default="f1_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me", alias="POSTGRES_PASSWORD")

    fastf1_cache_dir: Path = Field(
        default=ROOT_DIR / "data/raw/fastf1_cache",
        alias="FASTF1_CACHE_DIR",
    )
    openf1_base_url: str = Field(
        default="https://api.openf1.org/v1",
        alias="OPENF1_BASE_URL",
    )
    openweathermap_api_key: str | None = Field(
        default=None,
        alias="OPENWEATHERMAP_API_KEY",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for reuse across the app."""

    return Settings()
