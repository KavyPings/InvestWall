"""Regression gate deciding whether a newly trained model should replace
the current default transformer_model in backend/app/config.py.

Run (after training):
    python -m ml.evaluate --model ml/models/muril-scam-classifier \
        --known-tricky ml/eval/known_tricky.jsonl --baseline-f1 <rule-only-f1>
"""
from __future__ import annotations

import argparse

from ml.schema import read_jsonl


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


def evaluate_known_tricky(model_dir: str, known_tricky_path: str) -> float:
    from transformers import pipeline

    classifier = pipeline("text-classification", model=model_dir, truncation=True)
    examples = read_jsonl(known_tricky_path)

    correct = 0
    for ex in examples:
        result = classifier(ex.text[:512])[0]
        predicted_label = result["label"].lower()
        is_scam_prediction = "scam" in predicted_label
        is_scam_actual = ex.label.value == "scam"
        if is_scam_prediction == is_scam_actual:
            correct += 1

    return correct / len(examples)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--known-tricky", default="ml/eval/known_tricky.jsonl")
    parser.add_argument("--baseline-f1", type=float, required=True)
    parser.add_argument("--new-f1", type=float, required=True)
    args = parser.parse_args()

    accuracy = evaluate_known_tricky(args.model, args.known_tricky)
    ok, reason = should_promote(
        new_metrics={"f1": args.new_f1},
        baseline_metrics={"f1": args.baseline_f1},
        known_tricky_accuracy=accuracy,
    )
    print(f"known_tricky accuracy: {accuracy:.3f}")
    print(f"Promote: {ok} ({reason})")


if __name__ == "__main__":
    main()
