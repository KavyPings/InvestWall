"""Central configuration via environment / .env (pydantic-settings).

All heavy or network-dependent capabilities are behind flags that default to a
mode which runs with only the base `requirements.txt` installed and no network.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "InvestWall"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = ""

    # Database — empty => SQLite fallback file next to the app.
    database_url: str = ""

    # Cache — empty => in-memory fallback.
    redis_url: str = ""

    # Optional model / feature flags
    enable_transformers: bool = False
    enable_whisper: bool = False
    enable_qr: bool = False
    enable_dns: bool = True

    # Model choices (used only when the matching flag is on)
    transformer_model: str = "mrm8488/bert-tiny-finetuned-sms-spam-detection"
    whisper_model: str = "tiny"

    # Privacy — when False, raw input previews and sender are NOT persisted;
    # only scores/evidence reasons/metadata are stored.
    store_raw_content: bool = True

    # LLM
    llm_provider: str = "template"  # template | ollama | hosted
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    hosted_llm_api_key: str = ""
    hosted_llm_model: str = "claude-haiku-4-5-20251001"
    hosted_llm_base_url: str = "https://api.anthropic.com"

    # Uploads
    max_upload_mb: int = 50
    video_sample_frames: int = 16

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return "sqlite:///./investwall.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
