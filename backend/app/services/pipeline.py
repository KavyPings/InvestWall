"""Pipeline orchestrator — the InvestWall "AI Pipeline" (PRD §9 / §11).

Wires: Content Router -> modality engines -> Phishing + Authenticity engines ->
Evidence Fusion -> LLM explanation -> Trust Score -> persistence.

Engines are instantiated once (models/pipelines lazy-load on first use) and
reused across requests.
"""
from __future__ import annotations

import logging

from app.core.evidence import EvidenceBundle, Modality
from app.core.fusion import EvidenceFusion, FusionResult
from app.core.router import ContentRouter
from app.engines.audio_engine import AudioEngine
from app.engines.authenticity_engine import AuthenticityEngine
from app.engines.base import Payload
from app.engines.image_engine import ImageEngine
from app.engines.phishing_engine import PhishingEngine
from app.engines.text_engine import TextEngine
from app.engines.video_engine import VideoEngine
from app.llm.base import ExplanationInput, build_explainer
from app.services.extract import extract_document_text

logger = logging.getLogger("investwall.pipeline")


class AnalysisPipeline:
    def __init__(self) -> None:
        self.router = ContentRouter()
        self.text_engine = TextEngine()
        self.image_engine = ImageEngine()
        self.video_engine = VideoEngine()
        self.audio_engine = AudioEngine(text_engine=self.text_engine)
        self.phishing_engine = PhishingEngine()
        self.authenticity_engine = AuthenticityEngine()
        self.fusion = EvidenceFusion()
        self.explainer = build_explainer()

    # ---- public API ----
    def analyze_text(self, text: str, source: str | None = None,
                     sender: str | None = None) -> dict:
        payload = Payload(modality=Modality.TEXT, text=text, source=source, sender=sender)
        return self._run(payload)

    def analyze_file(self, data: bytes, filename: str | None, content_type: str | None,
                     source: str | None = None, sender: str | None = None) -> dict:
        modality = self.router.route_file(filename, content_type, data)
        payload = Payload(
            modality=modality, data=data, filename=filename,
            content_type=content_type, source=source, sender=sender,
        )
        return self._run(payload)

    # ---- core ----
    def _run(self, payload: Payload) -> dict:
        modality = payload.modality
        combined = EvidenceBundle(engine="pipeline", modality=modality)
        engine_errors: dict[str, str] = {}

        # Documents: extract text, then treat as text for downstream engines.
        if modality is Modality.DOCUMENT and payload.data is not None:
            extracted = extract_document_text(payload.data, payload.filename)
            payload.text = extracted
            payload.meta["extracted_chars"] = len(extracted)

        # 1) Modality-specific detector(s).
        for bundle in self._run_modality_engines(payload):
            self._merge(combined, bundle, engine_errors)

        # 2) Text-derived engines run whenever we have text (incl. documents,
        #    transcripts merged in extras by the audio engine).
        text_for_analysis = payload.text or combined.extras.get("transcript")
        if text_for_analysis:
            tp = Payload(
                modality=modality, text=text_for_analysis,
                source=payload.source, sender=payload.sender,
            )
            self._merge(combined, self.phishing_engine.safe_analyze(tp), engine_errors)
            self._merge(combined, self.authenticity_engine.safe_analyze(tp), engine_errors)
        else:
            # Still evaluate sender authenticity for media with a known sender.
            self._merge(combined, self.authenticity_engine.safe_analyze(payload), engine_errors)

        # 3) Fuse -> 4) Explain -> 5) Score.
        fusion: FusionResult = self.fusion.fuse(combined)
        explanation = self.explainer.safe_explain(
            ExplanationInput(
                modality=modality, fusion=fusion,
                top_evidence=fusion.evidence, source=payload.source,
            )
        )

        return self._to_report(payload, modality, fusion, explanation,
                                combined, engine_errors)

    def _run_modality_engines(self, payload: Payload):
        m = payload.modality
        if m is Modality.TEXT:
            yield self.text_engine.safe_analyze(payload)
        elif m is Modality.IMAGE:
            yield self.image_engine.safe_analyze(payload)
        elif m is Modality.VIDEO:
            yield self.video_engine.safe_analyze(payload)
        elif m is Modality.AUDIO:
            yield self.audio_engine.safe_analyze(payload)
        elif m is Modality.DOCUMENT:
            # Text engine over extracted text; document bytes could also feed the
            # image/metadata engine for scanned PDFs (kept simple here).
            yield self.text_engine.safe_analyze(payload)
        # UNKNOWN: no modality engine; phishing/authenticity may still apply.

    @staticmethod
    def _merge(combined: EvidenceBundle, bundle: EvidenceBundle, errors: dict) -> None:
        combined.extend(bundle)
        if bundle.error:
            errors[bundle.engine] = bundle.error

    def _to_report(self, payload, modality, fusion, explanation, combined, errors) -> dict:
        preview = None
        if payload.text:
            preview = payload.text[:400]

        evidence = [
            {
                "signal": e.signal,
                "component": e.component.value,
                "score": round(e.score, 4),
                "reason": e.reason,
            }
            for e in fusion.evidence
        ]

        return {
            "modality": modality.value,
            "source": payload.source,
            "sender": payload.sender,
            "filename": payload.filename,
            "input_preview": preview,
            "trust_score": fusion.trust_score,
            "band": fusion.band.key,
            "band_label": fusion.band.label,
            "band_color": fusion.band.color,
            "confidence": fusion.confidence,
            "primary_threat": fusion.primary_threat,
            "component_scores": fusion.component_scores,
            "explanation": explanation,
            "llm_provider": self.explainer.provider,
            "evidence": evidence,
            "extras": {k: v for k, v in combined.extras.items() if k != "transcript"}
            | ({"transcript": combined.extras["transcript"]} if "transcript" in combined.extras else {}),
            "engine_errors": errors,
        }


_pipeline: AnalysisPipeline | None = None


def get_pipeline() -> AnalysisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline()
    return _pipeline
