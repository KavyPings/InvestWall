"""Unit tests for individual detection engines."""
from __future__ import annotations

import io

from app.core.evidence import Component, Modality
from app.engines.authenticity_engine import AuthenticityEngine
from app.engines.base import Payload
from app.engines.image_engine import ImageEngine
from app.engines.phishing_engine import (
    PhishingEngine,
    extract_urls,
    registered_domain,
)
from app.engines.text_engine import TextEngine

SCAM = (
    "URGENT! SEBI has approved GUARANTEED 40% monthly returns on this stock. "
    "Act now, limited time only! Verify your demat account and click "
    "http://bit.ly/sebi-invest to claim your risk-free profit today!!!"
)


def _scores(bundle, component):
    return [e.score for e in bundle.items if e.component == component]


def test_text_engine_flags_scam():
    b = TextEngine().analyze(Payload(modality=Modality.TEXT, text=SCAM))
    phishing = _scores(b, Component.PHISHING)
    assert phishing, "expected phishing/scam evidence"
    assert max(phishing) >= 0.7


def test_text_engine_benign():
    text = (
        "Hi, are we still meeting for coffee tomorrow at 5pm near the office? "
        "Let me know if that time works for you or if you'd prefer later."
    )
    b = TextEngine().analyze(Payload(modality=Modality.TEXT, text=text))
    phishing = _scores(b, Component.PHISHING)
    assert not phishing or max(phishing) < 0.5


def test_phishing_engine_urls_and_shortener():
    b = PhishingEngine().analyze(Payload(modality=Modality.TEXT, text=SCAM))
    signals = {e.signal for e in b.items}
    assert "url_shortener" in signals
    assert b.extras["urls"]


def test_extract_and_registered_domain():
    urls = extract_urls("go to http://bit.ly/x and www.nseindia.com/page")
    assert any("bit.ly" in u for u in urls)
    assert registered_domain("http://sub.nseindia.com/foo") == "nseindia.com"


def test_phishing_brand_impersonation():
    text = "Login at http://sebi-verify.xyz/account to keep your account active"
    b = PhishingEngine().analyze(Payload(modality=Modality.TEXT, text=text))
    signals = {e.signal for e in b.items}
    assert "brand_impersonation" in signals or "suspicious_tld" in signals


def test_authenticity_official_sender():
    b = AuthenticityEngine().analyze(
        Payload(modality=Modality.TEXT, text="Official circular from SEBI",
                sender="notice@sebi.gov.in")
    )
    signals = {e.signal for e in b.items}
    assert "verified_official_domain" in signals
    auth = [e.score for e in b.items if e.component == Component.AUTHENTICITY]
    assert min(auth) < 0.2  # low risk


def test_authenticity_impersonation_claim():
    b = AuthenticityEngine().analyze(
        Payload(modality=Modality.TEXT, text="This is an official SEBI approved scheme",
                sender="admin@sebi-india-verify.com")
    )
    auth = [e.score for e in b.items if e.component == Component.AUTHENTICITY]
    assert auth and max(auth) >= 0.7  # high risk claimed-but-unverified


def test_text_engine_flags_paraphrased_guaranteed_return_scam():
    # A paraphrase that doesn't match the literal FINANCIAL_SCAM_RULES regexes
    # word-for-word, but uses a keyword newly added from the scam-quote bank.
    # Note: the engine always emits a low-score "no_phishing_indicators"
    # baseline (~0.12) when no rule fires, so a bare "evidence exists" check
    # would pass vacuously — assert a real signal fired with a real score.
    text = (
        "Join our exclusive trading circle, members are seeing consistent "
        "payouts every single week with a no-loss approach to every trade."
    )
    b = TextEngine().analyze(Payload(modality=Modality.TEXT, text=text))
    signals = {e.signal for e in b.items}
    phishing = _scores(b, Component.PHISHING)
    assert "no_phishing_indicators" not in signals
    assert phishing and max(phishing) >= 0.3


def test_transformer_score_recognizes_scam_label(monkeypatch):
    import app.engines.text_engine as text_engine_module

    class _FakeClassifier:
        def __call__(self, text):
            return [{"label": "scam", "score": 0.93}]

    class _FakeSettings:
        enable_transformers = True

    monkeypatch.setattr(text_engine_module, "_get_transformer", lambda: _FakeClassifier())
    monkeypatch.setattr(text_engine_module, "get_settings", lambda: _FakeSettings())

    bundle = TextEngine().analyze(
        Payload(modality=Modality.TEXT, text="Some message long enough to classify")
    )
    signals = {e.signal: e for e in bundle.items}
    assert "transformer_spam" in signals
    assert signals["transformer_spam"].score == 0.93


def test_image_engine_on_generated_png():
    # A tiny flat synthetic PNG: no EXIF, ultra-smooth => AI/metadata signals.
    from PIL import Image

    img = Image.new("RGB", (128, 128), (123, 200, 90))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    b = ImageEngine().analyze(
        Payload(modality=Modality.IMAGE, data=buf.getvalue(), filename="x.png")
    )
    assert b.error is None
    signals = {e.signal for e in b.items}
    assert "missing_exif" in signals
