"""InvestWall backend — FastAPI application entrypoint.

Implements the AI pipeline described in the PRD (§7/§9/§11): content is routed by
modality, analysed by specialised engines, fused into a Trust Score, and
explained by the LLM layer. See app/services/pipeline.py for orchestration.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import analyze, health, history
from app.config import get_settings
from app.db.base import init_db

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("investwall")

app = FastAPI(
    title="InvestWall API",
    version=__version__,
    description=(
        "AI-driven detection of synthetic media & phishing attacks for retail "
        "investors. Multimodal detection + evidence fusion + explainable Trust Score."
    ),
)

# CORS — the Android app and any web dashboard consume this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_prefix = settings.api_prefix.rstrip("/")
app.include_router(health.router, prefix=_prefix)
app.include_router(analyze.router, prefix=_prefix)
app.include_router(history.router, prefix=_prefix)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    logger.info(
        "InvestWall %s started (llm=%s, db=%s)",
        __version__, settings.llm_provider,
        "sqlite" if settings.effective_database_url.startswith("sqlite") else "postgres",
    )


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": f"{_prefix}/health",
    }
