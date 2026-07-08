from __future__ import annotations

from ml.evaluate import evaluate_predictions, rule_only_predict, should_promote
from ml.schema import Example, Label, Register, Source


def test_promotes_when_both_thresholds_met():
    ok, reason = should_promote(
        new_metrics={"f1": 0.90},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.90,
    )
    assert ok is True


def test_rejects_when_known_tricky_accuracy_too_low():
    ok, reason = should_promote(
        new_metrics={"f1": 0.95},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.70,
    )
    assert ok is False
    assert "known_tricky" in reason


def test_rejects_when_f1_improvement_too_small():
    ok, reason = should_promote(
        new_metrics={"f1": 0.81},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.95,
    )
    assert ok is False
    assert "f1" in reason


def test_rule_only_predict_flags_obvious_scam():
    text = (
        "URGENT! SEBI has approved GUARANTEED 40% monthly returns on this stock. "
        "Act now, limited time only! Verify your demat account and click "
        "http://bit.ly/sebi-invest to claim your risk-free profit today!!!"
    )
    assert rule_only_predict(text) == "scam"


def test_rule_only_predict_leaves_benign_text_as_legit():
    text = (
        "Hi, are we still meeting for coffee tomorrow at 5pm near the office? "
        "Let me know if that time works for you or if you'd prefer later."
    )
    assert rule_only_predict(text) == "legit"


def test_evaluate_predictions_computes_metrics_from_injected_predict_fn():
    examples = [
        Example(text="a", label=Label.SCAM, source=Source.CURATED, register=Register.ENGLISH),
        Example(text="b", label=Label.SCAM, source=Source.CURATED, register=Register.ENGLISH),
        Example(text="c", label=Label.LEGIT, source=Source.CURATED, register=Register.ENGLISH),
        Example(text="d", label=Label.LEGIT, source=Source.CURATED, register=Register.ENGLISH),
    ]
    # predicts "scam" for a and c, "legit" for b and d:
    # a: correct (scam->scam), b: wrong (scam->legit), c: wrong (legit->scam), d: correct
    predictions = {"a": "scam", "b": "legit", "c": "scam", "d": "legit"}

    metrics = evaluate_predictions(examples, lambda text: predictions[text])

    assert metrics["accuracy"] == 0.5
    assert set(metrics.keys()) >= {"accuracy", "precision", "recall", "f1"}
