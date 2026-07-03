"""History endpoints — list stored reports and fetch one by id."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import EvidenceItem, HistoryItem, TrustReport
from app.db.base import get_session
from app.db import repository

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[HistoryItem])
def list_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
) -> list[HistoryItem]:
    rows = repository.list_reports(db, limit=limit, offset=offset)
    return [
        HistoryItem(
            id=r.id,
            created_at=r.created_at,
            modality=r.modality,
            source=r.source,
            trust_score=r.trust_score,
            band=r.band,
            band_label=r.band_label,
            primary_threat=r.primary_threat,
            input_preview=r.input_preview,
        )
        for r in rows
    ]


@router.get("/report/{report_id}", response_model=TrustReport)
def get_report(report_id: str, db: Session = Depends(get_session)) -> TrustReport:
    r = repository.get_report(db, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return TrustReport(
        id=r.id,
        created_at=r.created_at,
        modality=r.modality,
        source=r.source,
        sender=r.sender,
        filename=r.filename,
        input_preview=r.input_preview,
        trust_score=r.trust_score,
        band=r.band,
        band_label=r.band_label,
        confidence=r.confidence,
        primary_threat=r.primary_threat,
        component_scores=r.component_scores or {},
        explanation=r.explanation,
        llm_provider=r.llm_provider,
        evidence=[
            EvidenceItem(signal=e.signal, component=e.component, score=e.score, reason=e.reason)
            for e in r.evidence
        ],
    )
