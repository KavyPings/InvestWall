"""Shared prompt construction for LLM-backed explainers.

The LLM reasons over *structured evidence only* (tech-stack §10) — never the raw
content — which keeps small instruction-tuned models sufficient and avoids
re-doing detection.
"""
from __future__ import annotations

from app.llm.base import ExplanationInput

SYSTEM_PROMPT = (
    "You are InvestWall's explanation module. You are given structured evidence "
    "from specialised fraud/synthetic-media detectors and a computed Trust Score. "
    "Explain to a non-technical retail investor, in 3-5 short sentences, why the "
    "content received this score and what they should do. Do NOT invent evidence "
    "beyond what is provided. Be calm, clear, and actionable."
)


def build_user_prompt(data: ExplanationInput) -> str:
    f = data.fusion
    lines = [
        f"Modality: {data.modality.value}",
        f"Source: {data.source or 'unknown'}",
        f"Trust Score: {f.trust_score}/100 ({f.band.label})",
        f"Confidence: {int(f.confidence * 100)}%",
        f"Primary threat: {f.primary_threat or 'none'}",
        "Component risk scores (0=clean, 1=malicious):",
    ]
    for k, v in f.component_scores.items():
        lines.append(f"  - {k}: {v}")
    lines.append("Top evidence signals:")
    for e in data.top_evidence[:8]:
        lines.append(f"  - ({e.score:.2f}) {e.reason}")
    lines.append(
        "\nWrite the explanation now for the investor. End with a one-line "
        "recommendation."
    )
    return "\n".join(lines)
