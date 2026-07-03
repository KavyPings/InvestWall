"""End-to-end API tests against the full pipeline (template LLM, offline)."""
from __future__ import annotations

SCAM = (
    "URGENT! SEBI has approved GUARANTEED 40% monthly returns. Act now, "
    "limited time! Verify your demat account at http://bit.ly/sebi-x !!!"
)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "template"


def test_analyze_scam_is_high_risk(client):
    r = client.post("/analyze", json={"text": SCAM, "source": "whatsapp"})
    assert r.status_code == 200
    body = r.json()
    assert body["band"] == "high_risk"
    assert body["trust_score"] < 40
    assert body["primary_threat"]
    assert body["explanation"]
    assert any(e["component"] == "phishing" for e in body["evidence"])
    assert body["id"]


def test_analyze_benign_message(client):
    text = (
        "Hey, thanks for lunch today! Let's catch up again next week. "
        "I'll text you once I know my schedule."
    )
    r = client.post("/analyze", json={"text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["trust_score"] >= 40


def test_official_sender_raises_trust(client):
    r = client.post("/analyze", json={
        "text": "Please find attached the official SEBI circular for Q3.",
        "sender": "circulars@sebi.gov.in",
        "source": "email",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["trust_score"] >= 60
    assert "authenticity" in body["component_scores"]


def test_history_and_report_roundtrip(client):
    created = client.post("/analyze", json={"text": SCAM}).json()
    rid = created["id"]

    hist = client.get("/history?limit=5")
    assert hist.status_code == 200
    assert any(item["id"] == rid for item in hist.json())

    one = client.get(f"/report/{rid}")
    assert one.status_code == 200
    assert one.json()["id"] == rid

    missing = client.get("/report/doesnotexist")
    assert missing.status_code == 404


def test_analyze_image_file(client):
    import io
    from PIL import Image

    img = Image.new("RGB", (96, 96), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    r = client.post(
        "/analyze/file",
        files={"file": ("test.png", buf.getvalue(), "image/png")},
        data={"source": "gallery"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["modality"] == "image"
    assert "ai" in body["component_scores"] or "metadata" in body["component_scores"]
