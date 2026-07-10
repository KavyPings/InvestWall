"""Liveness + capability reporting."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.api.schemas import HealthResponse
from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    db = "sqlite" if settings.effective_database_url.startswith("sqlite") else "postgresql"
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        llm_provider=settings.llm_provider,
        features={
            "transformers": settings.enable_transformers,
            "whisper": settings.enable_whisper,
            "image_model": settings.enable_image_model,
            "audio_model": settings.enable_audio_model,
            "qr": settings.enable_qr,
            "dns": settings.enable_dns,
            "store_raw_content": settings.store_raw_content,
            "transformer_loaded": _loaded("app.engines.text_engine", "transformer_loaded"),
            "image_model_loaded": _loaded("app.engines.image_engine", "image_model_loaded"),
            "image_ai_model_loaded": _loaded("app.engines.image_engine", "image_ai_model_loaded"),
            "audio_model_loaded": _loaded("app.engines.audio_engine", "audio_model_loaded"),
        },
        database=db,
    )


def _loaded(module: str, fn: str) -> bool:
    try:
        import importlib

        return bool(getattr(importlib.import_module(module), fn)())
    except Exception:  # pragma: no cover
        return False
