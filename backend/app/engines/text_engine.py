"""Module 1 — Text Analysis Engine (PRD §6).

Pipeline: cleaning -> tokenization/NER (spaCy) -> stylometric AI-likelihood ->
rule-based phishing & financial-scam scoring -> optional transformer classifier.

Only the base requirements are needed; spaCy's model and Transformers are
lazy-loaded and degrade gracefully if unavailable.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter

from app.config import get_settings
from app.core.evidence import Component, EvidenceBundle, Modality
from app.engines.base import Engine, Payload
from app.knowledge.phishing_rules import (
    CREDENTIAL_RULES,
    FINANCIAL_SCAM_RULES,
    RISKY_KEYWORDS,
    URGENCY_RULES,
)

logger = logging.getLogger("investwall.engine.text")

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_RE = re.compile(r"[.!?]+")

# Lazily-initialised singletons.
_NLP = None
_NLP_TRIED = False
_TRANSFORMER = None
_TRANSFORMER_TRIED = False


def _get_nlp():
    global _NLP, _NLP_TRIED
    if _NLP is not None or _NLP_TRIED:
        return _NLP
    _NLP_TRIED = True
    try:
        import spacy

        try:
            _NLP = spacy.load("en_core_web_sm", disable=["lemmatizer"])
        except OSError:
            # Model not downloaded — fall back to a blank pipeline with a
            # sentencizer so tokenization still works.
            _NLP = spacy.blank("en")
            if "sentencizer" not in _NLP.pipe_names:
                _NLP.add_pipe("sentencizer")
            logger.warning("spaCy model en_core_web_sm not found; using blank pipeline")
    except Exception:  # pragma: no cover
        logger.warning("spaCy unavailable; text engine uses regex tokenization only")
        _NLP = None
    return _NLP


def _get_transformer():
    global _TRANSFORMER, _TRANSFORMER_TRIED
    if _TRANSFORMER is not None or _TRANSFORMER_TRIED:
        return _TRANSFORMER
    _TRANSFORMER_TRIED = True
    try:
        from transformers import pipeline

        model = get_settings().transformer_model
        _TRANSFORMER = pipeline("text-classification", model=model, truncation=True)
        logger.info("Loaded transformer classifier: %s", model)
    except Exception as exc:  # pragma: no cover
        logger.warning("Transformer classifier unavailable: %s", exc)
        _TRANSFORMER = None
    return _TRANSFORMER


def transformer_loaded() -> bool:
    return _TRANSFORMER is not None


def _stylometry_ai_score(text: str) -> tuple[float, str]:
    """Heuristic AI-generated-text likelihood from stylometric regularity.

    LLM prose tends to be low-burstiness (uniform sentence length), lexically
    smooth, and low on typos/contractions. We combine a few cheap signals.
    Returns (score 0..1, reason).
    """
    words = _WORD_RE.findall(text)
    if len(words) < 25:
        return 0.0, ""  # too short to judge reliably

    sentences = [s for s in _SENT_RE.split(text) if s.strip()]
    if len(sentences) < 2:
        return 0.15, "Single-block text; limited stylometric signal."

    lengths = [len(_WORD_RE.findall(s)) for s in sentences if _WORD_RE.findall(s)]
    if len(lengths) < 2:
        return 0.15, ""
    mean_len = sum(lengths) / len(lengths)
    var = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std = math.sqrt(var)
    # Burstiness: low coefficient of variation => machine-like uniformity.
    cv = std / mean_len if mean_len else 1.0
    uniformity = max(0.0, 1.0 - min(cv / 0.6, 1.0))  # 0 = varied, 1 = uniform

    # Lexical diversity (type-token ratio). Very smooth, mid-range TTR is
    # common in generated marketing text.
    lower = [w.lower() for w in words]
    ttr = len(set(lower)) / len(lower)
    diversity_flag = 1.0 if 0.35 <= ttr <= 0.62 else 0.0

    # Human-writing markers reduce AI likelihood.
    contractions = len(re.findall(r"\b\w+'\w+\b", text))
    typo_ish = len(re.findall(r"\b\w{2,}(\w)\1\1", text))  # rough
    human_markers = min((contractions + typo_ish) / max(len(sentences), 1), 1.0)

    score = 0.6 * uniformity + 0.25 * diversity_flag + 0.15 * (mean_len > 14)
    score = max(0.0, score - 0.25 * human_markers)
    score = round(min(score, 1.0), 3)

    reason = (
        "Uniform sentence rhythm and smooth phrasing typical of AI-generated text."
        if score >= 0.5
        else "Writing style is broadly consistent with human authoring."
    )
    return score, reason


class TextEngine(Engine):
    name = "text"

    def analyze(self, payload: Payload) -> EvidenceBundle:
        settings = get_settings()
        bundle = self._bundle(Modality.TEXT)
        text = (payload.text or "").strip()
        if not text:
            return bundle

        clean = re.sub(r"\s+", " ", text)

        # --- Tokenization / NER (spaCy, optional) ---
        orgs: list[str] = []
        persons: list[str] = []
        nlp = _get_nlp()
        if nlp is not None:
            try:
                doc = nlp(clean[:20000])
                orgs = sorted({e.text for e in getattr(doc, "ents", []) if e.label_ == "ORG"})
                persons = sorted({e.text for e in getattr(doc, "ents", []) if e.label_ == "PERSON"})
                bundle.extras["entities"] = {"orgs": orgs, "persons": persons}
            except Exception:  # pragma: no cover
                pass

        # --- Stylometric AI likelihood ---
        # Only surface an AI signal when it is meaningfully elevated. A weak
        # "probably human" reading is *not* evidence of safety for text — a
        # human-written message can still be a scam — so we exclude it from
        # fusion rather than letting it dilute the phishing axis.
        ai_score, ai_reason = _stylometry_ai_score(clean)
        if ai_score >= 0.4:
            bundle.add(
                "ai_text_stylometry", ai_score, ai_reason,
                Component.AI, weight=1.0, ai_likelihood=ai_score,
            )

        # --- Rule-based scam / phishing / urgency scoring ---
        self._apply_rules(bundle, clean, FINANCIAL_SCAM_RULES, Component.PHISHING, "scam")
        self._apply_rules(bundle, clean, CREDENTIAL_RULES, Component.PHISHING, "credential")
        self._apply_rules(bundle, clean, URGENCY_RULES, Component.PHISHING, "urgency", weight=0.7)
        self._apply_keywords(bundle, clean)

        # --- Optional transformer classifier ---
        if settings.enable_transformers:
            self._transformer_score(bundle, clean)

        # --- Clean baseline ---
        # If nothing phishing/scam-like fired, the absence of indicators is a
        # low-risk signal in its own right. Without this, an innocuous message
        # (no signals at all) would fuse to a neutral 50 and be mislabelled
        # "Potentially Manipulated" — a false positive the PRD wants to avoid.
        # This applies to any non-empty text, including very short ones like
        # "hi" (which otherwise had no components at all).
        has_phishing = any(i.component is Component.PHISHING for i in bundle.items)
        if not has_phishing and clean:
            # Slightly higher residual risk for very short text, where we simply
            # have little to judge on, so confidence stays modest.
            word_count = len(_WORD_RE.findall(clean))
            baseline = 0.2 if word_count < 3 else 0.12
            bundle.add(
                "no_phishing_indicators", baseline,
                "No phishing, scam, or urgency indicators were detected in the text.",
                Component.PHISHING, weight=0.5,
            )

        return bundle

    def _apply_rules(self, bundle, text, rules, component, tag, weight=1.0):
        for pattern, w, reason in rules:
            if pattern.search(text):
                bundle.add(
                    f"{tag}_rule", w, reason, component,
                    weight=weight, pattern=pattern.pattern,
                )

    def _apply_keywords(self, bundle, text):
        lower = text.lower()
        hits = Counter()
        for kw, w in RISKY_KEYWORDS.items():
            if kw in lower:
                hits[kw] = w
        if hits:
            top = max(hits.values())
            words = ", ".join(sorted(hits))
            bundle.add(
                "risky_keywords", min(top + 0.05 * (len(hits) - 1), 1.0),
                f"Contains high-risk terms: {words}.",
                Component.PHISHING, weight=0.6, keywords=list(hits),
            )

    def _transformer_score(self, bundle, text):
        clf = _get_transformer()
        if clf is None:
            return
        try:
            out = clf(text[:512])[0]
            label = str(out.get("label", "")).lower()
            conf = float(out.get("score", 0.0))
            if "spam" in label or label in {"label_1", "1"}:
                bundle.add(
                    "transformer_spam", conf,
                    "Neural classifier flags this as spam/scam-like.",
                    Component.PHISHING, weight=1.1, model_confidence=conf,
                )
        except Exception:  # pragma: no cover
            pass
