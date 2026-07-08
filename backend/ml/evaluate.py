"""Regression gate deciding whether a newly trained model should replace
the current default transformer_model in backend/app/config.py.

Compares three things:
1. The rule-only engine's F1 on the held-out test.jsonl split (baseline).
2. The trained model's F1 on that same split (must beat baseline by a margin).
3. The trained model's accuracy on the hand-curated known_tricky.jsonl set
   (the real bar, since it's designed to be harder than the training data).

Run (after training):
    python -m ml.evaluate --model ml/models/muril-scam-classifier \
        --test ml/data/processed/test.jsonl --known-tricky ml/eval/known_tricky.jsonl
"""
from __future__ import annotations

import argparse
from typing import Callable

from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from ml.schema import Example, read_jsonl


def should_promote(
    new_metrics: dict,
    baseline_metrics: dict,
    known_tricky_accuracy: float,
    min_known_tricky_accuracy: float = 0.85,
    min_f1_improvement: float = 0.05,
) -> tuple[bool, str]:
    if known_tricky_accuracy < min_known_tricky_accuracy:
        return False, (
            f"known_tricky accuracy {known_tricky_accuracy:.2f} is below the "
            f"minimum {min_known_tricky_accuracy:.2f}"
        )

    f1_improvement = new_metrics["f1"] - baseline_metrics["f1"]
    if f1_improvement < min_f1_improvement:
        return False, (
            f"f1 improvement {f1_improvement:.3f} is below the minimum "
            f"{min_f1_improvement:.3f} over baseline"
        )

    return True, "passes both thresholds"


def rule_only_predict(text: str, threshold: float = 0.5) -> str:
    """Predicts "scam"/"legit" using only the existing rule-based engines
    (no ML) — the baseline the trained model must beat."""
    from app.core.evidence import Component, Modality
    from app.engines.base import Payload
    from app.engines.phishing_engine import PhishingEngine
    from app.engines.text_engine import TextEngine

    payload = Payload(modality=Modality.TEXT, text=text)
    bundle = TextEngine().analyze(payload)
    bundle.extend(PhishingEngine().analyze(payload))
    score = bundle.component_score(Component.PHISHING) or 0.0
    return "scam" if score >= threshold else "legit"


def evaluate_predictions(examples: list[Example], predict_fn: Callable[[str], str]) -> dict:
    """Computes accuracy/precision/recall/f1 (positive class = "scam") for
    predict_fn's output against each example's true label."""
    y_true = [ex.label.value for ex in examples]
    y_pred = [predict_fn(ex.text) for ex in examples]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label="scam", zero_division=0,
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def build_model_predict_fn(model_dir: str) -> Callable[[str], str]:
    from transformers import pipeline

    classifier = pipeline("text-classification", model=model_dir, truncation=True)

    def predict(text: str) -> str:
        result = classifier(text[:512])[0]
        label = str(result["label"]).lower()
        return "scam" if "scam" in label else "legit"

    return predict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--test", default="ml/data/processed/test.jsonl")
    parser.add_argument("--known-tricky", default="ml/eval/known_tricky.jsonl")
    args = parser.parse_args()

    test_examples = read_jsonl(args.test)

    print(f"Evaluating rule-only baseline on {len(test_examples)} held-out test examples...")
    baseline_metrics = evaluate_predictions(test_examples, rule_only_predict)
    print(f"  baseline: {baseline_metrics}")

    print("Loading trained model and evaluating on the same test set...")
    model_predict = build_model_predict_fn(args.model)
    model_metrics = evaluate_predictions(test_examples, model_predict)
    print(f"  model:    {model_metrics}")

    known_tricky_examples = read_jsonl(args.known_tricky)
    known_tricky_accuracy = evaluate_predictions(known_tricky_examples, model_predict)["accuracy"]
    print(f"known_tricky accuracy: {known_tricky_accuracy:.3f}")

    ok, reason = should_promote(
        new_metrics=model_metrics,
        baseline_metrics=baseline_metrics,
        known_tricky_accuracy=known_tricky_accuracy,
    )
    print(f"Promote: {ok} ({reason})")


if __name__ == "__main__":
    main()
