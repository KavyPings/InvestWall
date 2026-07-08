"""Near-duplicate removal for the combined dataset via embedding cosine
similarity — catches paraphrase-level duplicates that exact-text hashing
would miss (important since synthetic generation intentionally produces
many paraphrases of the same archetype).
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from ml.schema import Example


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # avoid div-by-zero; a zero vector stays zero
    return vectors / norms


def dedupe(
    examples: list[Example],
    embed_fn: Callable[[list[str]], list[list[float]]],
    threshold: float = 0.92,
) -> list[Example]:
    """Greedy near-duplicate removal: keeps the first occurrence of each
    cluster of examples whose embeddings are >= threshold cosine-similar.

    Vectorized with numpy (normalize once, then a running matrix-vector dot
    product against already-kept rows) rather than a pure-Python O(n^2)
    loop. At real dataset scale (~53k examples) the naive pure-Python
    version was an estimated ~1.4 billion interpreted cosine calls — many
    hours; this does the equivalent comparisons as numpy/BLAS matrix-vector
    products, which is seconds to low minutes.
    """
    if not examples:
        return []

    raw_vectors = np.asarray(embed_fn([ex.text for ex in examples]), dtype=np.float32)
    normalized = _normalize_rows(raw_vectors)

    kept_vectors = np.empty_like(normalized)
    kept_count = 0
    kept: list[Example] = []

    for ex, vec in zip(examples, normalized):
        if kept_count > 0 and (kept_vectors[:kept_count] @ vec).max() >= threshold:
            continue
        kept_vectors[kept_count] = vec
        kept_count += 1
        kept.append(ex)

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
