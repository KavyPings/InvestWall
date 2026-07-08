from __future__ import annotations

import os

from ml.schema import Label, Register, Source, read_jsonl

KNOWN_TRICKY_PATH = os.path.join(os.path.dirname(__file__), "..", "eval", "known_tricky.jsonl")


def test_known_tricky_set_is_balanced_and_covers_both_registers():
    examples = read_jsonl(KNOWN_TRICKY_PATH)

    assert len(examples) >= 20
    labels = [e.label for e in examples]
    assert labels.count(Label.SCAM) == labels.count(Label.LEGIT)

    registers = {e.register for e in examples}
    assert Register.ENGLISH in registers
    assert Register.HINGLISH in registers

    assert all(e.source == Source.CURATED for e in examples)
    assert all(e.text.strip() for e in examples)
