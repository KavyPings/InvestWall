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

    # Model / feature flags. ON by default; each model lazy-loads and degrades
    # gracefully (falls back to rules/heuristics) if its libraries/weights are
    # unavailable, so the service still boots with only the base requirements.
    enable_transformers: bool = True
    enable_whisper: bool = True
    enable_image_model: bool = True
    enable_qr: bool = False
    enable_dns: bool = True

    # Model choices (used only when the matching flag is on)
    # Uses the locally-trained MuRIL model if present, else the loader falls back
    # to `transformer_fallback_model` (which downloads automatically).
    transformer_model: str = "./ml/models/muril-scam-classifier"
    transformer_fallback_model: str = "mrm8488/bert-tiny-finetuned-sms-spam-detection"
    whisper_model: str = "tiny"
    # Deepfake/face-manipulation detector (run on cropped faces).
    image_model: str = "dima806/deepfake_vs_real_image_detection"
    # General AI-generated-image detector (whole image; catches non-face
    # synthetic content like fake charts / news screenshots).
    image_ai_model: str = "Organika/sdxl-detector"

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
