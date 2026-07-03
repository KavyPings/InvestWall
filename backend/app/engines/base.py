"""Base class shared by all detection engines.

Each engine is a self-contained, independently upgradeable module (tech-stack
§1 modularity). Heavy dependencies are lazy-loaded so the service always boots.
An engine receives a ``Payload`` and returns an ``EvidenceBundle``.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.evidence import EvidenceBundle, Modality

logger = logging.getLogger("investwall.engine")


@dataclass
class Payload:
    """Normalised input handed to an engine."""

    modality: Modality
    text: str | None = None
    data: bytes | None = None          # raw file bytes for media/documents
    filename: str | None = None
    content_type: str | None = None
    source: str | None = None          # sms | email | whatsapp | telegram | ...
    sender: str | None = None          # email address / phone / handle if known
    meta: dict[str, Any] = field(default_factory=dict)


class Engine(ABC):
    name: str = "engine"

    @abstractmethod
    def analyze(self, payload: Payload) -> EvidenceBundle:  # pragma: no cover
        ...

    def _bundle(self, modality: Modality) -> EvidenceBundle:
        return EvidenceBundle(engine=self.name, modality=modality)

    def safe_analyze(self, payload: Payload) -> EvidenceBundle:
        """Never raise — a failing engine degrades gracefully."""
        try:
            return self.analyze(payload)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Engine %s failed", self.name)
            bundle = self._bundle(payload.modality)
            bundle.error = f"{type(exc).__name__}: {exc}"
            return bundle
