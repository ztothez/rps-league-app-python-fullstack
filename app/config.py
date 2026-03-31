from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    rps_token: str = Field(alias="RPS_TOKEN")
    rps_base_url: str = Field(default="https://assignments.example.com", alias="RPS_BASE_URL")
    database_url: str = Field(default="sqlite:///./rps_league.db", alias="DATABASE_URL")
    sync_interval_seconds: int = Field(default=120, alias="SYNC_INTERVAL_SECONDS")
    sync_pages_per_run: int = Field(default=10, alias="SYNC_PAGES_PER_RUN")
    initial_sync_pages: int = Field(default=20, alias="INITIAL_SYNC_PAGES")


settings = Settings()
