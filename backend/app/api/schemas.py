"""Pydantic request/response models — the Android app's API contract."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw content to analyse")
    source: str | None = Field(None, description="sms|email|whatsapp|telegram|...")
    sender: str | None = Field(None, description="Email/phone/handle if known")


class EvidenceItem(BaseModel):
    signal: str
    component: str
    score: float
    reason: str


class TrustReport(BaseModel):
    id: str | None = None
    created_at: datetime | None = None
    modality: str
    source: str | None = None
    sender: str | None = None
    filename: str | None = None
    input_preview: str | None = None

    trust_score: int
    band: str
    band_label: str
    band_color: str | None = None
    confidence: float
    primary_threat: str | None = None

    component_scores: dict[str, float] = {}
    explanation: str
    llm_provider: str = "template"
    evidence: list[EvidenceItem] = []
    extras: dict = {}
    engine_errors: dict = {}


class HistoryItem(BaseModel):
    id: str
    created_at: datetime
    modality: str
    source: str | None = None
    trust_score: int
    band: str
    band_label: str
    primary_threat: str | None = None
    input_preview: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    llm_provider: str
    features: dict[str, bool]
    database: str
