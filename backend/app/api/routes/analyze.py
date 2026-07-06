"""Analysis endpoints — text and file upload."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import AnalyzeTextRequest, TrustReport
from app.config import get_settings
from app.db.base import get_session
from app.db import repository
from app.services.pipeline import get_pipeline

router = APIRouter(tags=["analysis"])


def _persist_and_build(report: dict, db: Session) -> TrustReport:
    """Persist a pipeline result and return the API model."""
    # Privacy: optionally avoid persisting the raw preview / sender server-side.
    store_raw = get_settings().store_raw_content
    report_row = repository.save_report(
        db,
        report_data={
            "modality": report["modality"],
            "source": report.get("source"),
            "sender": report.get("sender") if store_raw else None,
            "filename": report.get("filename"),
            "input_preview": report.get("input_preview") if store_raw else None,
            "trust_score": report["trust_score"],
            "band": report["band"],
            "band_label": report["band_label"],
            "confidence": report["confidence"],
            "primary_threat": report.get("primary_threat"),
            "component_scores": report["component_scores"],
            "explanation": report["explanation"],
            "llm_provider": report["llm_provider"],
        },
        evidence=[
            {
                "signal": e["signal"],
                "component": e["component"],
                "score": e["score"],
                "reason": e["reason"],
            }
            for e in report["evidence"]
        ],
    )
    return TrustReport(
        id=report_row.id,
        created_at=report_row.created_at,
        **{k: v for k, v in report.items() if k not in {"source", "sender", "filename"}},
        source=report.get("source"),
        sender=report.get("sender"),
        filename=report.get("filename"),
    )


@router.post("/analyze", response_model=TrustReport)
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_session)) -> TrustReport:
    report = get_pipeline().analyze_text(req.text, source=req.source, sender=req.sender)
    return _persist_and_build(report, db)


@router.post("/analyze/file", response_model=TrustReport)
async def analyze_file(
    file: UploadFile = File(...),
    source: str | None = Form(None),
    sender: str | None = Form(None),
    db: Session = Depends(get_session),
) -> TrustReport:
    settings = get_settings()
    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_mb} MB limit",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    report = get_pipeline().analyze_file(
        data, filename=file.filename, content_type=file.content_type,
        source=source, sender=sender,
    )
    if report["modality"] == "unknown":
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported or undetectable content type for '{file.filename}'",
        )
    return _persist_and_build(report, db)
