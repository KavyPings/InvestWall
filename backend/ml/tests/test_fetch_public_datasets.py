from __future__ import annotations

from ml.schema import Label, Register, Source
from ml.scripts.fetch_public_datasets import normalize_phishing_email, normalize_sms_spam


def test_normalize_sms_spam_maps_labels():
    rows = [
        {"sms": "Free entry in 2 a wkly comp to win FA Cup", "label": 1},
        {"sms": "Ok lar... Joking wif u oni...", "label": 0},
    ]
    examples = normalize_sms_spam(rows)

    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[0].source == Source.PUBLIC
    assert examples[0].register == Register.ENGLISH
    assert examples[1].label == Label.LEGIT


def test_normalize_phishing_email_maps_labels():
    # Real column names from the zefang-liu/phishing-email-dataset schema:
    # "Email Text" (str) and "Email Type" ("Phishing Email" | "Safe Email").
    rows = [
        {"Email Text": "Verify your account immediately or it will be suspended", "Email Type": "Phishing Email"},
        {"Email Text": "Meeting moved to 3pm tomorrow, see you there", "Email Type": "Safe Email"},
    ]
    examples = normalize_phishing_email(rows)

    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[1].label == Label.LEGIT


def test_normalize_phishing_email_skips_blank_or_missing_text():
    rows = [
        {"Email Text": "   ", "Email Type": "Phishing Email"},
        {"Email Text": None, "Email Type": "Safe Email"},
        {"Email Text": "Real email body here", "Email Type": "Safe Email"},
    ]
    examples = normalize_phishing_email(rows)
    assert len(examples) == 1
    assert examples[0].text == "Real email body here"


def test_normalize_skips_blank_text():
    rows = [{"sms": "   ", "label": 1}, {"sms": "Real message here", "label": 0}]
    examples = normalize_sms_spam(rows)
    assert len(examples) == 1
    assert examples[0].text == "Real message here"
