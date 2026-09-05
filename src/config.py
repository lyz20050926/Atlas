from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "mock"
    aws_region: str = "us-east-1"
    aws_profile: str = ""
    bedrock_model_id: str = ""
    bedrock_learning_model_id: str = ""
    bedrock_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    bedrock_read_timeout_seconds: float = Field(default=65.0, gt=0, le=180)
    bedrock_max_attempts: int = Field(default=2, ge=1, le=5)
    google_books_api_key: str = ""
    database_path: str = "data/nexmind_atlas.db"
    app_mode: str = "development"
    http_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    http_max_retries: int = Field(default=2, ge=0, le=5)
    api_cache_ttl_hours: float = Field(default=24.0, gt=0, le=720)
    max_search_results: int = Field(default=6, ge=1, le=10)
    max_search_iterations: int = Field(default=3, ge=1, le=3)

    @property
    def demo_mode(self) -> bool:
        return self.app_mode.strip().lower() == "demo"

    @property
    def resolved_database_path(self) -> Path:
        path = Path(self.database_path)
        return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
