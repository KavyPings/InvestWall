"""Persistence models — mirrors the data the Android Room cache will hold."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScanReport(Base):
    __tablename__ = "scan_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    modality: Mapped[str] = mapped_column(String(16))
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    trust_score: Mapped[int] = mapped_column(Integer)
    band: Mapped[str] = mapped_column(String(32))
    band_label: Mapped[str] = mapped_column(String(48))
    confidence: Mapped[float] = mapped_column(Float)
    primary_threat: Mapped[str | None] = mapped_column(String(64), nullable=True)

    component_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    llm_provider: Mapped[str] = mapped_column(String(16), default="template")

    evidence: Mapped[list["EvidenceLog"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="desc(EvidenceLog.score)",
    )


class EvidenceLog(Base):
    __tablename__ = "evidence_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("scan_reports.id", ondelete="CASCADE"))

    signal: Mapped[str] = mapped_column(String(64))
    component: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)

    report: Mapped["ScanReport"] = relationship(back_populates="evidence")
