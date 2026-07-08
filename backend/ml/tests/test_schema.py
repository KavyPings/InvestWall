from __future__ import annotations

import json
import os
import tempfile

from ml.schema import Example, Label, Register, Source, read_jsonl, write_jsonl


def test_round_trip_write_and_read():
    examples = [
        Example(text="Guaranteed 40% returns!", label=Label.SCAM,
                source=Source.PUBLIC, register=Register.ENGLISH, archetype=None),
        Example(text="Aapka order execute ho gaya", label=Label.LEGIT,
                source=Source.CURATED, register=Register.HINGLISH,
                archetype="legit_broker_alert"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.jsonl")
        write_jsonl(examples, path)
        loaded = read_jsonl(path)

    assert loaded == examples


def test_jsonl_lines_are_valid_json():
    examples = [Example(text="hi", label=Label.LEGIT, source=Source.PUBLIC,
                         register=Register.ENGLISH)]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.jsonl")
        write_jsonl(examples, path)
        with open(path, encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]

    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["label"] == "legit"
    assert parsed["source"] == "public"
    assert parsed["register"] == "english"
