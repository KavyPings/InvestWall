"""LLM explanation layer contract (tech-stack §10).

The LLM *explains* evidence — it never performs detection. Every explainer
receives the structured fusion result + evidence and returns human-readable
prose. Implementations: template (default, deterministic), ollama, hosted.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.evidence import Evidence, Modality
from app.core.fusion import FusionResult


@dataclass
class ExplanationInput:
    modality: Modality
    fusion: FusionResult
    top_evidence: list[Evidence]
    source: str | None = None


class LLMExplainer(ABC):
    provider: str = "base"

    @abstractmethod
    def explain(self, data: ExplanationInput) -> str:  # pragma: no cover
        ...

    def safe_explain(self, data: ExplanationInput) -> str:
        try:
            text = self.explain(data)
            if text and text.strip():
                return text.strip()
        except Exception:  # pragma: no cover
            pass
        # Guaranteed fallback so the API always returns an explanation.
        from app.llm.template_explainer import TemplateExplainer

        return TemplateExplainer().explain(data)


def build_explainer():
    """Factory selecting the explainer from settings (with safe fallback)."""
    from app.config import get_settings

    provider = get_settings().llm_provider.lower().strip()
    if provider == "ollama":
        from app.llm.ollama_explainer import OllamaExplainer

        return OllamaExplainer()
    if provider == "hosted":
        from app.llm.hosted_explainer import HostedExplainer

        return HostedExplainer()
    from app.llm.template_explainer import TemplateExplainer

    return TemplateExplainer()
