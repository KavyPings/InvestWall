"""Evidence Fusion Layer (PRD §8 / tech-stack §11).

Combines per-component risk scores into a single Trust Score using the PRD
weighting, with renormalisation over only the components that are actually
present for a given piece of content (e.g. a plain SMS has no image score).

Weighting (risk contribution):
    AI Detection      30%
    Phishing          25%
    Source Reputation 15%
    Authenticity      20%
    Metadata          10%
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.evidence import Component, Evidence, EvidenceBundle
from app.core.trust_score import Band, band_for

COMPONENT_WEIGHTS: dict[Component, float] = {
    Component.AI: 0.30,
    Component.PHISHING: 0.25,
    Component.SOURCE: 0.15,
    Component.AUTHENTICITY: 0.20,
    Component.METADATA: 0.10,
}

# Human labels for the "primary threat category" output.
THREAT_LABELS: dict[Component, str] = {
    Component.AI: "AI-Generated / Synthetic Media",
    Component.PHISHING: "Phishing / Financial Scam",
    Component.SOURCE: "Untrusted Source",
    Component.AUTHENTICITY: "Unverified Authenticity",
    Component.METADATA: "Metadata / Provenance Anomaly",
}


@dataclass
class FusionResult:
    trust_score: int
    band: Band
    confidence: float
    primary_threat: str | None
    component_scores: dict[str, float]      # 0..1 risk per present component
    component_risk_weighted: dict[str, float]
    evidence: list[Evidence] = field(default_factory=list)


class EvidenceFusion:
    """Weighted aggregation + calibrated confidence."""

    def __init__(self, weights: dict[Component, float] | None = None) -> None:
        self.weights = weights or COMPONENT_WEIGHTS

    def fuse(self, bundle: EvidenceBundle) -> FusionResult:
        present: dict[Component, float] = {}
        for component in Component:
            score = bundle.component_score(component)
            if score is not None:
                present[component] = score

        # Authenticity is inverted: a *verified* authentic source lowers risk.
        # Engines emit authenticity as risk already (1 = unverifiable/spoofed,
        # 0 = fully verified), so no inversion is needed here — see
        # authenticity_engine.py for the convention.

        if not present:
            # Nothing to judge on — neutral, low confidence.
            return FusionResult(
                trust_score=50,
                band=band_for(50),
                confidence=0.1,
                primary_threat=None,
                component_scores={},
                component_risk_weighted={},
                evidence=list(bundle.items),
            )

        total_weight = sum(self.weights[c] for c in present) or 1.0
        weighted_risk = 0.0
        weighted_contrib: dict[str, float] = {}
        for component, score in present.items():
            w = self.weights[component] / total_weight
            contrib = score * w
            weighted_risk += contrib
            weighted_contrib[component.value] = round(contrib, 4)

        # Severity floor: a single decisive high-risk signal (e.g. an obvious
        # phishing giveaway or a strong deepfake tell) must not be fully diluted
        # by low-risk components. The overall risk can never fall far below the
        # strongest present component.
        strongest = max(present.values())
        weighted_risk = max(weighted_risk, strongest * 0.6)

        trust_score = int(round((1.0 - weighted_risk) * 100))
        trust_score = max(0, min(100, trust_score))

        primary_threat = self._primary_threat(present)
        confidence = self._confidence(present, bundle)

        return FusionResult(
            trust_score=trust_score,
            band=band_for(trust_score),
            confidence=round(confidence, 3),
            primary_threat=primary_threat,
            component_scores={c.value: round(s, 4) for c, s in present.items()},
            component_risk_weighted=weighted_contrib,
            evidence=sorted(bundle.items, key=lambda e: e.score, reverse=True),
        )

    def _primary_threat(self, present: dict[Component, float]) -> str | None:
        # The component contributing the most *weighted* risk.
        ranked = sorted(
            present.items(),
            key=lambda kv: kv[1] * self.weights[kv[0]],
            reverse=True,
        )
        top_component, top_score = ranked[0]
        if top_score < 0.35:
            return None  # nothing meaningfully risky
        return THREAT_LABELS[top_component]

    def _confidence(
        self, present: dict[Component, float], bundle: EvidenceBundle
    ) -> float:
        """Confidence grows with evidence coverage and signal decisiveness.

        - More components present => broader coverage.
        - Scores near 0 or 1 (decisive) => higher confidence than 0.5 (unsure).
        """
        coverage = len(present) / len(self.weights)
        decisiveness = sum(abs(s - 0.5) * 2 for s in present.values()) / len(present)
        n_signals = len([i for i in bundle.items]) or 1
        signal_bonus = min(n_signals / 12.0, 1.0)
        conf = 0.45 * coverage + 0.40 * decisiveness + 0.15 * signal_bonus
        return max(0.1, min(0.99, conf))
