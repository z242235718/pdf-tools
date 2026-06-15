from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./pdf_tools.db", alias="DATABASE_URL")
    storage_root: Path = Field(default=Path("../storage"), alias="STORAGE_ROOT")
    upload_retention_hours: int = Field(default=24, alias="UPLOAD_RETENTION_HOURS")
    output_retention_hours: int = Field(default=24, alias="OUTPUT_RETENTION_HOURS")
    max_upload_mb: int = Field(default=100, alias="MAX_UPLOAD_MB")
    max_pdf_pages: int = Field(default=500, alias="MAX_PDF_PAGES")
    max_concurrent_tasks_per_user: int = Field(default=2, alias="MAX_CONCURRENT_TASKS_PER_USER")
    fingerprint_secret: str = Field(
        default="dev-fingerprint-secret-do-not-use-in-prod",
        alias="FINGERPRINT_SECRET",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
