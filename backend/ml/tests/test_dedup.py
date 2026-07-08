from __future__ import annotations

from ml.dedup import dedupe
from ml.schema import Example, Label, Register, Source


def _fake_embed_fn(vectors_by_text: dict[str, list[float]]):
    def embed(texts: list[str]) -> list[list[float]]:
        return [vectors_by_text[t] for t in texts]
    return embed


def test_dedupe_removes_near_identical_vectors():
    examples = [
        Example(text="Guaranteed 40% returns!", label=Label.SCAM,
                source=Source.PUBLIC, register=Register.ENGLISH),
        Example(text="Guaranteed 40 percent returns!!", label=Label.SCAM,
                source=Source.SYNTHETIC, register=Register.ENGLISH),
        Example(text="Meeting moved to 3pm tomorrow", label=Label.LEGIT,
                source=Source.PUBLIC, register=Register.ENGLISH),
    ]
    # First two are near-identical vectors (cosine ~1.0); third is orthogonal.
    vectors = {
        "Guaranteed 40% returns!": [1.0, 0.0],
        "Guaranteed 40 percent returns!!": [0.999, 0.001],
        "Meeting moved to 3pm tomorrow": [0.0, 1.0],
    }
    result = dedupe(examples, embed_fn=_fake_embed_fn(vectors), threshold=0.95)

    assert len(result) == 2
    kept_texts = {e.text for e in result}
    assert "Meeting moved to 3pm tomorrow" in kept_texts
    # exactly one of the two near-duplicates survives
    assert len(kept_texts & {"Guaranteed 40% returns!", "Guaranteed 40 percent returns!!"}) == 1


def test_dedupe_keeps_all_when_no_duplicates():
    examples = [
        Example(text="a", label=Label.LEGIT, source=Source.PUBLIC, register=Register.ENGLISH),
        Example(text="b", label=Label.LEGIT, source=Source.PUBLIC, register=Register.ENGLISH),
    ]
    vectors = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
    result = dedupe(examples, embed_fn=_fake_embed_fn(vectors), threshold=0.95)
    assert len(result) == 2
