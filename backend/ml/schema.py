"""Shared example schema for the text scam/phishing training dataset.

Used by every stage of the ml/ pipeline (fetch, dedup, generate, build,
train, evaluate) so scripts can be composed without re-parsing formats.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum


class Label(str, Enum):
    LEGIT = "legit"
    SCAM = "scam"


class Register(str, Enum):
    ENGLISH = "english"
    HINGLISH = "hinglish"
    MIXED = "mixed"


class Source(str, Enum):
    PUBLIC = "public"
    SYNTHETIC = "synthetic"
    CURATED = "curated"  # hand-written eval-only examples (known_tricky.jsonl)


@dataclass
class Example:
    text: str
    label: Label
    source: Source
    register: Register
    archetype: str | None = None  # e.g. "guaranteed_returns_paraphrase"; None for raw public data

    def to_json(self) -> str:
        d = asdict(self)
        d["label"] = self.label.value
        d["source"] = self.source.value
        d["register"] = self.register.value
        return json.dumps(d, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict) -> "Example":
        return Example(
            text=d["text"],
            label=Label(d["label"]),
            source=Source(d["source"]),
            register=Register(d["register"]),
            archetype=d.get("archetype"),
        )


def write_jsonl(examples: list[Example], path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(ex.to_json() + "\n")


def read_jsonl(path: str) -> list[Example]:
    examples: list[Example] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(Example.from_dict(json.loads(line)))
    return examples
