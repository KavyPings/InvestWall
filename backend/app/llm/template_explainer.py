"""Deterministic template explainer (DEFAULT — no external dependency).

Turns structured evidence + trust band into the kind of user-friendly prose
shown in tech-stack §10, entirely offline. Also used as the guaranteed fallback
whenever an optional LLM provider fails.
"""
from __future__ import annotations

from app.llm.base import ExplanationInput, LLMExplainer

_BAND_OPENER = {
    "high_risk": "This content is assessed as HIGH RISK.",
    "potentially_manipulated": "This content is POTENTIALLY MANIPULATED — treat it with caution.",
    "highly_authentic": "This content appears HIGHLY AUTHENTIC.",
}

_MODALITY_NOUN = {
    "text": "message",
    "image": "image",
    "video": "video",
    "audio": "voice note",
    "document": "document",
    "unknown": "content",
}


class TemplateExplainer(LLMExplainer):
    provider = "template"

    def explain(self, data: ExplanationInput) -> str:
        fusion = data.fusion
        band = fusion.band
        noun = _MODALITY_NOUN.get(data.modality.value, "content")
        opener = _BAND_OPENER.get(band.key, "Analysis complete.")

        parts: list[str] = [
            f"{opener} Trust Score: {fusion.trust_score}/100 "
            f"({band.label}, confidence {int(fusion.confidence * 100)}%)."
        ]

        if fusion.primary_threat:
            parts.append(f"Primary concern: {fusion.primary_threat}.")

        reasons = self._dedupe_reasons(data.top_evidence)
        if reasons:
            bullet = " ".join(f"• {r}" for r in reasons[:5])
            parts.append(
                f"This {noun} was flagged because: {bullet}"
            )
        elif band.key == "highly_authentic":
            parts.append(
                f"No significant risk signals were found in this {noun}, and "
                "available source checks were consistent with a legitimate origin."
            )

        parts.append(self._advice(band.key, fusion.primary_threat))
        return " ".join(parts)

    @staticmethod
    def _dedupe_reasons(evidence) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for e in evidence:
            if e.score < 0.3:
                continue
            key = e.reason.strip()
            if key and key not in seen:
                seen.add(key)
                out.append(key)
        return out

    @staticmethod
    def _advice(band_key: str, threat: str | None) -> str:
        if band_key == "high_risk":
            base = ("Recommendation: do NOT click links, share OTP/credentials, "
                    "or transfer money. Independently verify through the official "
                    "website or a known contact before acting.")
            if threat and "Synthetic" in threat:
                base += (" Since the media may be AI-generated, do not trust its "
                         "identity claims without out-of-band confirmation.")
            return base
        if band_key == "potentially_manipulated":
            return ("Recommendation: verify the sender and any claims through an "
                    "official channel before taking financial action.")
        return ("You can proceed with normal caution, but always confirm major "
                "financial decisions through official sources.")
