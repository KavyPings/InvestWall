from __future__ import annotations

import os
import tempfile

from ml.schema import Example, Label, Register, Source, read_jsonl, write_jsonl
from ml.scripts.build_dataset import combine_and_split


def _identity_embed_fn(texts: list[str]) -> list[list[float]]:
    # Each text maps to a genuinely orthogonal one-hot vector (not a 1-D
    # scalar — two positive scalars are always cosine-collinear regardless
    # of magnitude) so nothing dedupes here; dedup behavior itself is
    # covered by test_dedup.py.
    n = len(texts)
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def test_combine_and_split_writes_three_files_with_all_examples():
    examples = [
        Example(text=f"scam {i}", label=Label.SCAM, source=Source.PUBLIC,
                register=Register.ENGLISH)
        for i in range(20)
    ] + [
        Example(text=f"legit {i}", label=Label.LEGIT, source=Source.PUBLIC,
                register=Register.ENGLISH)
        for i in range(20)
    ]

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.jsonl")
        write_jsonl(examples, in_path)

        counts = combine_and_split(
            [in_path], out_dir=tmp, val_frac=0.2, test_frac=0.2,
            seed=1, embed_fn=_identity_embed_fn,
        )

        train = read_jsonl(os.path.join(tmp, "train.jsonl"))
        val = read_jsonl(os.path.join(tmp, "val.jsonl"))
        test = read_jsonl(os.path.join(tmp, "test.jsonl"))

    assert len(train) + len(val) + len(test) == 40
    assert counts == {"train": len(train), "val": len(val), "test": len(test)}
    # roughly stratified: both classes present in every split
    for split in (train, val, test):
        labels = {e.label for e in split}
        assert labels == {Label.SCAM, Label.LEGIT}


def test_combine_and_split_is_deterministic_for_a_fixed_seed():
    examples = [
        Example(text=f"item {i}", label=Label.SCAM if i % 2 == 0 else Label.LEGIT,
                source=Source.PUBLIC, register=Register.ENGLISH)
        for i in range(30)
    ]
    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.jsonl")
        write_jsonl(examples, in_path)

        combine_and_split([in_path], out_dir=os.path.join(tmp, "a"), seed=7,
                           embed_fn=_identity_embed_fn)
        combine_and_split([in_path], out_dir=os.path.join(tmp, "b"), seed=7,
                           embed_fn=_identity_embed_fn)

        train_a = read_jsonl(os.path.join(tmp, "a", "train.jsonl"))
        train_b = read_jsonl(os.path.join(tmp, "b", "train.jsonl"))

    assert [e.text for e in train_a] == [e.text for e in train_b]
