"""Evidence primitives shared across the pipeline.

An engine produces an ``EvidenceBundle``: a list of ``Evidence`` signals plus
per-fusion-component scores. Every signal carries a 0..1 score, a weight, and a
short human-readable reason string used by the LLM explanation layer.

Score convention: **higher score = more suspicious / more risk** (0 = clean,
1 = definitely malicious/synthetic). The fusion layer inverts risk into a Trust
Score at the end.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class Component(str, Enum):
    """Fusion components matching PRD §8 Trust Score weighting."""

    AI = "ai"                     # 30% — synthetic-media / AI-generation likelihood
    PHISHING = "phishing"         # 25% — phishing / scam risk
    SOURCE = "source"             # 15% — source / sender reputation
    AUTHENTICITY = "authenticity"  # 20% — verified authenticity of the source
    METADATA = "metadata"         # 10% — metadata / provenance anomalies


@dataclass
class Evidence:
    """A single explainable signal from an engine."""

    signal: str
    score: float                 # 0..1 risk (higher = more suspicious)
    reason: str
    component: Component
    weight: float = 1.0          # relative weight within its component
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.score = max(0.0, min(1.0, float(self.score)))
        self.weight = max(0.0, float(self.weight))


@dataclass
class EvidenceBundle:
    """All evidence produced by one engine for one piece of content."""

    engine: str
    modality: Modality
    items: list[Evidence] = field(default_factory=list)
    # Optional derived artefacts (transcript, extracted urls, etc.)
    extras: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def add(
        self,
        signal: str,
        score: float,
        reason: str,
        component: Component,
        weight: float = 1.0,
        **detail: Any,
    ) -> None:
        self.items.append(
            Evidence(
                signal=signal,
                score=score,
                reason=reason,
                component=component,
                weight=weight,
                detail=detail,
            )
        )

    def extend(self, other: "EvidenceBundle") -> None:
        self.items.extend(other.items)
        self.extras.update(other.extras)

    def component_score(self, component: Component) -> float | None:
        """Weighted-max blend of a component's signals, or None if absent.

        We combine the weighted mean with the max so a single strong signal is
        not diluted by many weak ones (important for a lone deepfake giveaway).
        """
        items = [i for i in self.items if i.component == component]
        if not items:
            return None
        total_w = sum(i.weight for i in items) or 1.0
        weighted_mean = sum(i.score * i.weight for i in items) / total_w
        strongest = max(i.score for i in items)
        return round(0.6 * weighted_mean + 0.4 * strongest, 4)
