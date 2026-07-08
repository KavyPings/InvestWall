from __future__ import annotations

from ml.evaluate import should_promote


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
