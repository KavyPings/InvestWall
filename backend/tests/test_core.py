"""Unit tests for the core pipeline primitives."""
from __future__ import annotations

from app.core.evidence import Component, EvidenceBundle, Modality
from app.core.fusion import COMPONENT_WEIGHTS, EvidenceFusion
from app.core.router import ContentRouter
from app.core.trust_score import band_for


def test_component_weights_sum_to_one():
    assert abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) < 1e-9


def test_trust_bands():
    assert band_for(92).key == "highly_authentic"
    assert band_for(45).key == "potentially_manipulated"
    assert band_for(15).key == "high_risk"
    assert band_for(75).key == "highly_authentic"
    assert band_for(39).key == "high_risk"


def test_router_text_and_files():
    r = ContentRouter()
    assert r.route_text("hello") is Modality.TEXT
    assert r.route_text("   ") is Modality.UNKNOWN
    assert r.route_file("a.png", None) is Modality.IMAGE
    assert r.route_file("clip.mp4", None) is Modality.VIDEO
    assert r.route_file("note.m4a", None) is Modality.AUDIO
    assert r.route_file("doc.pdf", None) is Modality.DOCUMENT
    assert r.route_file(None, "image/jpeg") is Modality.IMAGE
    # magic-byte sniff
    assert r.route_file(None, None, b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) is Modality.IMAGE


def test_fusion_high_risk_from_phishing():
    b = EvidenceBundle(engine="t", modality=Modality.TEXT)
    b.add("scam", 0.9, "guaranteed returns", Component.PHISHING, weight=1.0)
    b.add("ai", 0.7, "ai text", Component.AI, weight=1.0)
    res = EvidenceFusion().fuse(b)
    assert res.trust_score < 40
    assert res.band.key == "high_risk"
    assert res.primary_threat is not None


def test_fusion_authentic_when_clean():
    b = EvidenceBundle(engine="t", modality=Modality.TEXT)
    b.add("verified", 0.05, "official domain", Component.AUTHENTICITY, weight=1.0)
    b.add("trusted", 0.1, "known org", Component.SOURCE, weight=1.0)
    res = EvidenceFusion().fuse(b)
    assert res.trust_score >= 75
    assert res.band.key == "highly_authentic"


def test_fusion_renormalises_present_components():
    b = EvidenceBundle(engine="t", modality=Modality.TEXT)
    b.add("only", 1.0, "max risk", Component.PHISHING, weight=1.0)
    res = EvidenceFusion().fuse(b)
    # Single maxed component => score near 0 regardless of its 25% nominal weight.
    assert res.trust_score <= 5
