"""Combine public + synthetic example files, dedupe near-duplicates, and
produce a stratified train/val/test split.

Run: python -m ml.scripts.build_dataset \
    --in data/raw/public.jsonl data/synthetic/synthetic.jsonl \
    --out-dir data/processed
"""
from __future__ import annotations

import argparse
import os
from typing import Callable

from sklearn.model_selection import train_test_split

from ml.dedup import dedupe, sentence_transformer_embed_fn
from ml.schema import Example, read_jsonl, write_jsonl


def combine_and_split(
    input_paths: list[str],
    out_dir: str,
    dedupe_threshold: float = 0.92,
    val_frac: float = 0.1,
    test_frac: float = 0.1,
    seed: int = 42,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> dict[str, int]:
    all_examples: list[Example] = []
    for path in input_paths:
        all_examples.extend(read_jsonl(path))

    embed_fn = embed_fn or sentence_transformer_embed_fn()
    deduped = dedupe(all_examples, embed_fn=embed_fn, threshold=dedupe_threshold)

    labels = [ex.label.value for ex in deduped]
    train_val, test = train_test_split(
        deduped, test_size=test_frac, random_state=seed, stratify=labels,
    )
    train_val_labels = [ex.label.value for ex in train_val]
    relative_val_frac = val_frac / (1 - test_frac)
    train, val = train_test_split(
        train_val, test_size=relative_val_frac, random_state=seed,
        stratify=train_val_labels,
    )

    os.makedirs(out_dir, exist_ok=True)
    write_jsonl(train, os.path.join(out_dir, "train.jsonl"))
    write_jsonl(val, os.path.join(out_dir, "val.jsonl"))
    write_jsonl(test, os.path.join(out_dir, "test.jsonl"))

    return {"train": len(train), "val": len(val), "test": len(test)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="inputs", nargs="+", required=True)
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--dedupe-threshold", type=float, default=0.92)
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--test-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    counts = combine_and_split(
        args.inputs, args.out_dir, args.dedupe_threshold,
        args.val_frac, args.test_frac, args.seed,
    )
    print(f"Wrote splits: {counts}")


if __name__ == "__main__":
    main()
