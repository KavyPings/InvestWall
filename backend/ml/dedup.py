"""Near-duplicate removal for the combined dataset via embedding cosine
similarity — catches paraphrase-level duplicates that exact-text hashing
would miss (important since synthetic generation intentionally produces
many paraphrases of the same archetype).
"""
from __future__ import annotations

import math
from typing import Callable

from ml.schema import Example


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def dedupe(
    examples: list[Example],
    embed_fn: Callable[[list[str]], list[list[float]]],
    threshold: float = 0.92,
) -> list[Example]:
    """Greedy near-duplicate removal: keeps the first occurrence of each
    cluster of examples whose embeddings are >= threshold cosine-similar."""
    if not examples:
        return []

    vectors = embed_fn([ex.text for ex in examples])
    kept: list[Example] = []
    kept_vectors: list[list[float]] = []

    for ex, vec in zip(examples, vectors):
        is_duplicate = any(_cosine(vec, kv) >= threshold for kv in kept_vectors)
        if not is_duplicate:
            kept.append(ex)
            kept_vectors.append(vec)

    return kept


def sentence_transformer_embed_fn(
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> Callable[[list[str]], list[list[float]]]:
    """Real embedding function used in production runs (build_dataset.py).
    Multilingual model chosen so Hinglish text embeds meaningfully too."""
    from sentence_transformers import SentenceTransformer  # lazy import

    model = SentenceTransformer(model_name)

    def embed(texts: list[str]) -> list[list[float]]:
        return model.encode(texts, show_progress_bar=False).tolist()

    return embed
