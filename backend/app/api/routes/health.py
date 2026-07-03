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
            "qr": settings.enable_qr,
            "dns": settings.enable_dns,
        },
        database=db,
    )
