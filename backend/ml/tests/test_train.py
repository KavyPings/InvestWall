from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from ml.train import compute_metrics, id2label, label2id


def test_label_mappings_are_consistent():
    assert label2id == {"legit": 0, "scam": 1}
    assert id2label == {0: "legit", 1: "scam"}


def test_compute_metrics_reports_precision_recall_f1():
    # 4 examples: predictions [scam, scam, legit, legit], labels [scam, legit, legit, scam]
    logits = np.array([[0.1, 0.9], [0.2, 0.8], [0.9, 0.1], [0.8, 0.2]])
    labels = np.array([1, 0, 0, 1])

    metrics = compute_metrics((logits, labels))

    assert set(metrics.keys()) >= {"accuracy", "precision", "recall", "f1"}
    assert metrics["accuracy"] == pytest.approx(0.5)
