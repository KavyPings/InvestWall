"""Repository helpers for persisting and reading Trust Reports."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import EvidenceLog, ScanReport


def save_report(db: Session, report_data: dict, evidence: list[dict]) -> ScanReport:
    report = ScanReport(**report_data)
    report.evidence = [EvidenceLog(**e) for e in evidence]
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, report_id: str) -> ScanReport | None:
    stmt = (
        select(ScanReport)
        .where(ScanReport.id == report_id)
        .options(selectinload(ScanReport.evidence))
    )
    return db.execute(stmt).scalar_one_or_none()


def list_reports(db: Session, limit: int = 50, offset: int = 0) -> list[ScanReport]:
    stmt = (
        select(ScanReport)
        .order_by(ScanReport.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(ScanReport.evidence))
    )
    return list(db.execute(stmt).scalars().all())
