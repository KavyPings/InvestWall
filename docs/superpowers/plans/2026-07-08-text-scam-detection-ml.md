# Text Scam/Phishing Detection ML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the text engine's generic transformer hook with a trained MuRIL scam/phishing classifier (English + Hinglish), fed by a large public+synthetic dataset, and make backend analysis run automatically (no button) for every incoming SMS and shared text.

**Architecture:** A new `backend/ml/` pipeline (separate from the runtime `app/`) fetches public datasets, generates synthetic India/Hinglish-specific examples via an LLM API, dedupes and splits them, and fine-tunes MuRIL. The trained checkpoint plugs into the existing `_transformer_score()` hook in `text_engine.py` with no API changes. On the Android side, `SmsAnalysisWorker` and `ShareViewModel` change from local-only to local-then-auto-escalate, so every message is sent to the backend automatically while still showing an instant on-device result first.

**Tech Stack:** Python (HuggingFace `transformers`/`datasets`/`Trainer`, `sentence-transformers` for dedup, `scikit-learn` for stratified splits), MuRIL (`google/muril-base-cased`), Kotlin/Coroutines/WorkManager (existing Android stack).

## Global Constraints

- Model is backend-only; the Android APK never bundles any ML model (per approved design doc, `docs/superpowers/specs/2026-07-08-text-scam-detection-ml-design.md`).
- Binary label scheme: `"scam"` (risk) vs `"legit"` (no risk) — must match what `_transformer_score()` interprets.
- Target combined dataset size: ~50k–80k examples (public + synthetic English + synthetic Hinglish).
- New pipeline code lives in `backend/ml/`, isolated from `backend/app/` (the serving code).
- No changes to the `/analyze` API contract.
- Regression gate before promoting the model: must not break any of the existing 20 tests in `backend/tests/`, and must beat the rule-only baseline on the hand-curated `known_tricky.jsonl` set.
- Rule engine and stylometry heuristic keep running unchanged; the trained model only adds an additional evidence item.
- Never commit or push without the user explicitly asking in that message (global git rule).

---

### Task 1: `ml` package skeleton + shared example schema

**Files:**
- Create: `backend/ml/__init__.py`
- Create: `backend/ml/schema.py`
- Create: `backend/ml/tests/__init__.py`
- Create: `backend/ml/tests/test_schema.py`
- Create: `backend/ml/requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `Example` dataclass, `Label` enum (`LEGIT`, `SCAM`), `Register` enum (`ENGLISH`, `HINGLISH`, `MIXED`), `Source` enum (`PUBLIC`, `SYNTHETIC`, `CURATED`), `write_jsonl(examples: list[Example], path: str) -> None`, `read_jsonl(path: str) -> list[Example]` — every later task imports from `ml.schema`.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml'` (or `ml.schema`).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/schema.py
"""Shared example schema for the text scam/phishing training dataset.

Used by every stage of the ml/ pipeline (fetch, dedup, generate, build,
train, evaluate) so scripts can be composed without re-parsing formats.
"""
from __future__ import annotations

import json
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
```

```python
# backend/ml/__init__.py
```

```python
# backend/ml/tests/__init__.py
```

```
# backend/ml/requirements.txt
# ML pipeline deps (data prep + training). Isolated from backend/requirements*.txt
# since this code only runs during offline dataset/model prep, never in the
# serving app. Install with: pip install -r ml/requirements.txt
datasets==3.2.0
torch==2.5.1
transformers==4.48.0
sentence-transformers==3.3.1
scikit-learn==1.6.0
requests==2.32.3
```

Append to `.gitignore` (repo root):

```
# ML pipeline (backend/ml/)
backend/ml/data/raw/
backend/ml/models/
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_schema.py -v`
Expected: PASS (2 tests)

Note: running `python -m pytest` from `backend/` puts `backend/` on `sys.path`, so `ml` resolves the same way `app` already does for the existing test suite — no `conftest.py`/path changes needed.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/__init__.py backend/ml/schema.py backend/ml/tests/__init__.py backend/ml/tests/test_schema.py backend/ml/requirements.txt .gitignore
git commit -m "feat(ml): add shared example schema for scam-detection dataset pipeline"
```

---

### Task 2: Real scam-quote/keyword bank + rule expansion

**Files:**
- Create: `backend/app/knowledge/scam_quotes.py`
- Modify: `backend/app/knowledge/phishing_rules.py`
- Modify: `backend/tests/test_engines.py`

**Interfaces:**
- Produces: `SCAM_QUOTE_BANK: list[ScamQuote]` (dataclass with `text`, `archetype`, `note`) in `scam_quotes.py` — consumed later by `ml/scripts/generate_synthetic.py` (Task 5) as few-shot seed material, and by this task's own expansion of `RISKY_KEYWORDS` in `phishing_rules.py`.

This is a starter set illustrating well-documented Indian investment-scam
phrasing patterns (guaranteed-return pitches, fake regulator approval,
Telegram/WhatsApp tip-group recruitment, credential harvesting). **Before
running synthetic generation at full scale (Task 5), expand this list to
at least 150 entries** by pulling additional real quotes from the SEBI
investor-alerts page, RBI's public cautions list, and cybercrime.gov.in
advisories — this is manual domain research, not something to automate.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_engines.py — add at the end of the file
def test_text_engine_flags_paraphrased_guaranteed_return_scam():
    # A paraphrase that doesn't match the literal FINANCIAL_SCAM_RULES regexes
    # word-for-word, but uses a keyword newly added from the scam-quote bank.
    text = (
        "Join our exclusive trading circle — members are seeing consistent, "
        "no-loss weekly payouts and it's completely risk-free money for you."
    )
    b = TextEngine().analyze(Payload(modality=Modality.TEXT, text=text))
    phishing = _scores(b, Component.PHISHING)
    assert phishing, "expected phishing/scam evidence from expanded keyword bank"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/test_engines.py::test_text_engine_flags_paraphrased_guaranteed_return_scam -v`
Expected: FAIL — `assert phishing` raises `AssertionError` (no evidence yet), because "no-loss" / "risk-free money for you" isn't in `RISKY_KEYWORDS` yet.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/knowledge/scam_quotes.py
"""Curated bank of real/representative scam keywords and phrases, specific
to Indian securities-market fraud. Serves two purposes:

1. Source material for expanding RISKY_KEYWORDS / rule patterns in
   phishing_rules.py (this file's SCAM_QUOTE_BANK is folded in below).
2. Few-shot grounding seeds for ml/scripts/generate_synthetic.py, so
   LLM-generated synthetic examples stay anchored to real scam phrasing
   instead of drifting into generic, unrealistic text.

STARTER SET — expand to >=150 entries from SEBI investor-alert pages,
RBI's public cautions list, and cybercrime.gov.in advisories before running
generate_synthetic.py at full scale (see Task 5 of the implementation plan).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScamQuote:
    text: str
    archetype: str
    note: str


SCAM_QUOTE_BANK: list[ScamQuote] = [
    ScamQuote(
        "Guaranteed 40% returns every month, absolutely risk-free investment.",
        "guaranteed_returns",
        "Classic guaranteed-return pitch pattern.",
    ),
    ScamQuote(
        "SEBI has approved this scheme, your capital is 100% safe.",
        "fake_regulator_approval",
        "False regulator-approval claim.",
    ),
    ScamQuote(
        "Join our exclusive trading circle for consistent, no-loss weekly payouts.",
        "guaranteed_returns",
        "Paraphrase avoiding literal 'guaranteed returns' wording.",
    ),
    ScamQuote(
        "This is risk-free money for you, act before slots close tonight.",
        "guaranteed_returns",
        "Risk-free framing + urgency combined.",
    ),
    ScamQuote(
        "Our insider tip has hit target 9 out of 10 times this month.",
        "insider_tip",
        "Sure-shot/insider stock-tip pattern.",
    ),
    ScamQuote(
        "Double your capital in 15 days with our proven strategy.",
        "guaranteed_returns",
        "Multiply-your-money variant.",
    ),
    ScamQuote(
        "Your demat account will be suspended unless you verify your PAN now.",
        "credential_harvest",
        "Account-suspension threat to force credential disclosure.",
    ),
    ScamQuote(
        "Share the OTP you just received so we can confirm your identity.",
        "credential_harvest",
        "Direct OTP-sharing request.",
    ),
    ScamQuote(
        "Limited seats left in our VIP Telegram tips group, first month free.",
        "telegram_recruit",
        "Tips-group recruitment with false scarcity.",
    ),
    ScamQuote(
        "This penny stock is about to explode, insiders are already buying.",
        "pump_and_dump",
        "Pump-and-dump exhortation.",
    ),
    ScamQuote(
        "Convert your savings into a daily-payout crypto plan, withdraw profits every day.",
        "crypto_scheme",
        "Daily-payout crypto scheme pattern.",
    ),
    ScamQuote(
        "Congratulations, you've been selected for a government-backed wealth scheme.",
        "fake_regulator_approval",
        "Fake selection/eligibility framing.",
    ),
]

# Keyword -> weight additions derived from the quote bank above, folded into
# phishing_rules.RISKY_KEYWORDS. Weights follow the same 0..1 convention.
KEYWORD_ADDITIONS: dict[str, float] = {
    "risk-free money": 0.5,
    "no-loss": 0.45,
    "consistent payouts": 0.35,
    "double your capital": 0.5,
    "insider tip": 0.45,
    "sure-shot": 0.4,
    "daily-payout": 0.4,
    "vip telegram": 0.35,
    "government-backed wealth scheme": 0.45,
}
```

```python
# backend/app/knowledge/phishing_rules.py — modify near the end of RISKY_KEYWORDS
```

Modify `RISKY_KEYWORDS` in `backend/app/knowledge/phishing_rules.py`:

```python
from app.knowledge.scam_quotes import KEYWORD_ADDITIONS

# High-signal keywords that individually add mild risk.
RISKY_KEYWORDS: dict[str, float] = {
    "guaranteed": 0.4, "lottery": 0.5, "prize": 0.4, "winner": 0.4,
    "congratulations": 0.35, "claim now": 0.5, "free money": 0.6,
    "work from home": 0.3, "part time income": 0.35, "refund": 0.3,
    "wire transfer": 0.4, "gift card": 0.5, "bonus": 0.25,
    **KEYWORD_ADDITIONS,
}
```

(Add the `from app.knowledge.scam_quotes import KEYWORD_ADDITIONS` line to
the existing import block at the top of `phishing_rules.py`, and replace
the plain `RISKY_KEYWORDS = {...}` dict literal with the version above that
spreads in `KEYWORD_ADDITIONS`.)

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/test_engines.py -v`
Expected: PASS (all tests, including the new one — "risk-free money" now scores via `RISKY_KEYWORDS`)

- [ ] **Step 5: Commit**

```bash
git add backend/app/knowledge/scam_quotes.py backend/app/knowledge/phishing_rules.py backend/tests/test_engines.py
git commit -m "feat: add curated scam-quote bank and expand phishing keyword rules"
```

---

### Task 3: Fetch and normalize public datasets

**Files:**
- Create: `backend/ml/scripts/__init__.py`
- Create: `backend/ml/scripts/fetch_public_datasets.py`
- Create: `backend/ml/tests/test_fetch_public_datasets.py`

**Interfaces:**
- Consumes: `Example`, `Label`, `Register`, `Source`, `write_jsonl` from `ml.schema` (Task 1).
- Produces: `normalize_sms_spam(rows: list[dict]) -> list[Example]`, `normalize_phishing_email(rows: list[dict]) -> list[Example]`, `main(out_path: str) -> None` — `build_dataset.py` (Task 6) reads `main`'s output file.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_fetch_public_datasets.py
from __future__ import annotations

from ml.schema import Label, Register, Source
from ml.scripts.fetch_public_datasets import normalize_phishing_email, normalize_sms_spam


def test_normalize_sms_spam_maps_labels():
    rows = [
        {"sms": "Free entry in 2 a wkly comp to win FA Cup", "label": 1},
        {"sms": "Ok lar... Joking wif u oni...", "label": 0},
    ]
    examples = normalize_sms_spam(rows)

    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[0].source == Source.PUBLIC
    assert examples[0].register == Register.ENGLISH
    assert examples[1].label == Label.LEGIT


def test_normalize_phishing_email_maps_labels():
    rows = [
        {"text_combined": "Verify your account immediately or it will be suspended", "label": 1},
        {"text_combined": "Meeting moved to 3pm tomorrow, see you there", "label": 0},
    ]
    examples = normalize_phishing_email(rows)

    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[1].label == Label.LEGIT


def test_normalize_skips_blank_text():
    rows = [{"sms": "   ", "label": 1}, {"sms": "Real message here", "label": 0}]
    examples = normalize_sms_spam(rows)
    assert len(examples) == 1
    assert examples[0].text == "Real message here"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_fetch_public_datasets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.scripts.fetch_public_datasets'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/scripts/__init__.py
```

```python
# backend/ml/scripts/fetch_public_datasets.py
"""Download and normalize public scam/phishing/legit-text datasets into the
shared Example schema (ml/schema.py).

Sources (Hugging Face Hub dataset IDs — update here if a dataset moves):
- "sms_spam": SMS Spam Collection, ~5.5k rows, fields {"sms": str, "label": int}
  (0 = ham/legit, 1 = spam/scam).
- "zefang-liu/phishing-email-dataset": combined phishing/legit email corpus
  (built from Enron, Nazario, SpamAssassin, CEAS, Ling), fields
  {"text_combined": str, "label": int} (1 = phishing, 0 = legitimate).

Run: python -m ml.scripts.fetch_public_datasets --out data/raw/public.jsonl
"""
from __future__ import annotations

import argparse

from ml.schema import Example, Label, Register, Source, write_jsonl

SMS_SPAM_DATASET_ID = "sms_spam"
PHISHING_EMAIL_DATASET_ID = "zefang-liu/phishing-email-dataset"


def normalize_sms_spam(rows: list[dict]) -> list[Example]:
    examples = []
    for row in rows:
        text = (row.get("sms") or "").strip()
        if not text:
            continue
        label = Label.SCAM if int(row["label"]) == 1 else Label.LEGIT
        examples.append(Example(text=text, label=label, source=Source.PUBLIC,
                                 register=Register.ENGLISH))
    return examples


def normalize_phishing_email(rows: list[dict]) -> list[Example]:
    examples = []
    for row in rows:
        text = (row.get("text_combined") or "").strip()
        if not text:
            continue
        label = Label.SCAM if int(row["label"]) == 1 else Label.LEGIT
        examples.append(Example(text=text, label=label, source=Source.PUBLIC,
                                 register=Register.ENGLISH))
    return examples


def fetch_all() -> list[Example]:
    from datasets import load_dataset  # imported lazily; only needed at fetch time

    sms_rows = load_dataset(SMS_SPAM_DATASET_ID, split="train")
    email_rows = load_dataset(PHISHING_EMAIL_DATASET_ID, split="train")
    return normalize_sms_spam(list(sms_rows)) + normalize_phishing_email(list(email_rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/raw/public.jsonl")
    args = parser.parse_args()

    examples = fetch_all()
    write_jsonl(examples, args.out)
    print(f"Wrote {len(examples)} public examples to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_fetch_public_datasets.py -v`
Expected: PASS (3 tests). Note these tests call `normalize_*` directly with
in-memory fixture rows — they do not hit the network or import `datasets`,
so they run without the `ml/requirements.txt` deps installed.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/scripts/__init__.py backend/ml/scripts/fetch_public_datasets.py backend/ml/tests/test_fetch_public_datasets.py
git commit -m "feat(ml): add public dataset fetch/normalize script"
```

---

### Task 4: Near-duplicate dedup via sentence embeddings

**Files:**
- Create: `backend/ml/dedup.py`
- Create: `backend/ml/tests/test_dedup.py`

**Interfaces:**
- Consumes: `Example` from `ml.schema`.
- Produces: `dedupe(examples: list[Example], embed_fn: Callable[[list[str]], list[list[float]]], threshold: float = 0.92) -> list[Example]`, `sentence_transformer_embed_fn(model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> Callable[[list[str]], list[list[float]]]` — consumed by `build_dataset.py` (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_dedup.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.dedup'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/dedup.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_dedup.py -v`
Expected: PASS (2 tests). These use the fake `embed_fn`, so no
`sentence-transformers` install or model download is required to pass.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/dedup.py backend/ml/tests/test_dedup.py
git commit -m "feat(ml): add embedding-similarity dedup for training examples"
```

---

### Task 5: Synthetic Hinglish/English scam & legit generation (GPT-OSS-120B)

**Files:**
- Create: `backend/ml/scripts/generate_synthetic.py`
- Create: `backend/ml/tests/test_generate_synthetic.py`

**Interfaces:**
- Consumes: `Example`, `Label`, `Register`, `Source`, `write_jsonl` from `ml.schema`; `SCAM_QUOTE_BANK` from `app.knowledge.scam_quotes` (Task 2).
- Produces: `ARCHETYPES: list[Archetype]`, `build_prompt(archetype: Archetype, register: Register, label: Label, n: int, seed_quotes: list[str]) -> list[dict]` (chat messages), `parse_response(raw_text: str) -> list[str]`, `SyntheticGenerator.generate_batch(archetype, register, label, n) -> list[Example]` — consumed by this script's own `main()`, output file read by `build_dataset.py` (Task 6).

**Note on scale:** the `ARCHETYPES` list below is a starting set (10
entries x 2 labels x 3 registers). Per the design doc, expand this to
40–60 archetypes before the full-scale run — follow the same
`Archetype(id=..., description=..., seed_quotes=[...])` shape, sourcing
`seed_quotes` from the expanded `SCAM_QUOTE_BANK` (Task 2). Also confirm
which provider serves the GPT-OSS-120B key (Groq/Together/Fireworks/
OpenRouter/etc.) and set `--base-url` accordingly — all of these expose an
OpenAI-compatible `/chat/completions` endpoint, which is what
`call_gpt_oss` below targets.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_generate_synthetic.py
from __future__ import annotations

from ml.schema import Label, Register
from ml.scripts.generate_synthetic import (
    ARCHETYPES,
    SyntheticGenerator,
    build_prompt,
    parse_response,
)


def test_build_prompt_includes_register_and_seed_quotes():
    archetype = ARCHETYPES[0]
    messages = build_prompt(
        archetype, Register.HINGLISH, Label.SCAM, n=5,
        seed_quotes=["Guaranteed 40% returns every month."],
    )
    joined = " ".join(m["content"] for m in messages)
    assert "Hinglish" in joined
    assert "Guaranteed 40% returns every month." in joined
    assert "5" in joined


def test_parse_response_splits_numbered_list():
    raw = "1. First scam message here\n2. Second scam message here\n3. Third one"
    lines = parse_response(raw)
    assert lines == [
        "First scam message here",
        "Second scam message here",
        "Third one",
    ]


def test_parse_response_ignores_blank_lines():
    raw = "1. Only one\n\n\n"
    assert parse_response(raw) == ["Only one"]


def test_generate_batch_uses_injected_chat_fn():
    archetype = ARCHETYPES[0]
    calls = []

    def fake_chat_fn(messages: list[dict]) -> str:
        calls.append(messages)
        return "1. Example one\n2. Example two"

    gen = SyntheticGenerator(chat_fn=fake_chat_fn)
    examples = gen.generate_batch(archetype, Register.ENGLISH, Label.SCAM, n=2)

    assert len(calls) == 1
    assert len(examples) == 2
    assert examples[0].label == Label.SCAM
    assert examples[0].register == Register.ENGLISH
    assert examples[0].archetype == archetype.id
    assert examples[0].text == "Example one"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_generate_synthetic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.scripts.generate_synthetic'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/scripts/generate_synthetic.py
"""Generate synthetic scam/legit examples across English, Hinglish, and
mixed registers, using an LLM (GPT-OSS-120B via an OpenAI-compatible API)
seeded with real quotes from app.knowledge.scam_quotes.SCAM_QUOTE_BANK.

Run: python -m ml.scripts.generate_synthetic --out data/synthetic/synthetic.jsonl \
    --api-key $GPT_OSS_API_KEY --base-url https://api.<provider>.com/v1 \
    --model gpt-oss-120b --n-per-batch 40
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from typing import Callable

from app.knowledge.scam_quotes import SCAM_QUOTE_BANK
from ml.schema import Example, Label, Register, Source, write_jsonl


@dataclass(frozen=True)
class Archetype:
    id: str
    description: str
    seed_quotes: list[str]


def _seeds_for(archetype_id: str) -> list[str]:
    return [q.text for q in SCAM_QUOTE_BANK if q.archetype == archetype_id]


ARCHETYPES: list[Archetype] = [
    Archetype("guaranteed_returns", "Promises guaranteed/fixed high returns with no risk",
               _seeds_for("guaranteed_returns")),
    Archetype("fake_regulator_approval", "Falsely implies SEBI/RBI/NSE/BSE approval or endorsement",
               _seeds_for("fake_regulator_approval")),
    Archetype("insider_tip", "Sure-shot / insider stock tips with high win-rate claims",
               _seeds_for("insider_tip")),
    Archetype("credential_harvest", "Requests OTP/PIN/PAN/login under account-threat pretext",
               _seeds_for("credential_harvest")),
    Archetype("telegram_recruit", "Recruits into a paid tips Telegram/WhatsApp group",
               _seeds_for("telegram_recruit")),
    Archetype("pump_and_dump", "Pump-and-dump exhortation on a specific stock",
               _seeds_for("pump_and_dump")),
    Archetype("crypto_scheme", "Daily-payout crypto/forex scheme with profit promises",
               _seeds_for("crypto_scheme")),
    Archetype("legit_broker_alert", "Genuine order/margin/dividend notification from a broker",
               []),
    Archetype("legit_sebi_language", "Genuine SEBI-registered-adviser disclaimer language",
               []),
    Archetype("legit_otp_message", "Genuine OTP/verification message with standard security wording",
               []),
]


def build_prompt(
    archetype: Archetype, register: Register, label: Label, n: int, seed_quotes: list[str],
) -> list[dict]:
    register_instruction = {
        Register.ENGLISH: "Write in plain English, as typed in an SMS or WhatsApp message.",
        Register.HINGLISH: (
            "Write in Hinglish — natural Hindi-English code-mixed text in Roman "
            "script, exactly as commonly typed on Indian WhatsApp/SMS "
            "(e.g. mixing words like 'aapka', 'abhi', 'ho jayega')."
        ),
        Register.MIXED: (
            "Mix English and Hinglish freely across the batch, and include some "
            "informal typos/abbreviations as seen in real forwarded messages."
        ),
    }[register]

    label_instruction = (
        f"Each message must be a realistic example of: {archetype.description}."
        if label == Label.SCAM
        else (
            f"Each message must be a GENUINE, non-scam message related to: "
            f"{archetype.description}. It must NOT be a scam, even though it may "
            f"use similar vocabulary (e.g. mentioning SEBI, returns, or KYC in a "
            f"legitimate context)."
        )
    )

    seed_block = (
        "Here are real examples of this kind of message for style reference "
        "(do not copy verbatim, write new varied ones):\n"
        + "\n".join(f"- {q}" for q in seed_quotes)
        if seed_quotes
        else ""
    )

    user_content = (
        f"{label_instruction}\n{register_instruction}\n{seed_block}\n"
        f"Generate {n} distinct messages, varied in length and phrasing. "
        f"Return them as a numbered list, one message per line, no extra commentary."
    )

    return [
        {"role": "system", "content": "You generate training data for a financial-scam detection classifier."},
        {"role": "user", "content": user_content},
    ]


_NUMBERED_LINE_RE = re.compile(r"^\s*\d+[\.\)]\s*(.+?)\s*$")


def parse_response(raw_text: str) -> list[str]:
    lines = []
    for line in raw_text.splitlines():
        match = _NUMBERED_LINE_RE.match(line)
        if match:
            lines.append(match.group(1))
    return lines


def call_gpt_oss(messages: list[dict], api_key: str, base_url: str, model: str) -> str:
    """Real network call to an OpenAI-compatible chat completions endpoint."""
    import requests

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.9},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


class SyntheticGenerator:
    def __init__(self, chat_fn: Callable[[list[dict]], str]):
        self.chat_fn = chat_fn

    def generate_batch(
        self, archetype: Archetype, register: Register, label: Label, n: int,
    ) -> list[Example]:
        messages = build_prompt(archetype, register, label, n, archetype.seed_quotes)
        raw = self.chat_fn(messages)
        lines = parse_response(raw)
        return [
            Example(text=text, label=label, source=Source.SYNTHETIC,
                    register=register, archetype=archetype.id)
            for text in lines
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/synthetic/synthetic.jsonl")
    parser.add_argument("--api-key", default=os.environ.get("GPT_OSS_API_KEY", ""))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="gpt-oss-120b")
    parser.add_argument("--n-per-batch", type=int, default=40)
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Set --api-key or GPT_OSS_API_KEY")

    def chat_fn(messages: list[dict]) -> str:
        return call_gpt_oss(messages, args.api_key, args.base_url, args.model)

    generator = SyntheticGenerator(chat_fn=chat_fn)
    all_examples: list[Example] = []
    registers = [Register.ENGLISH, Register.HINGLISH, Register.MIXED]
    labels = [Label.SCAM, Label.LEGIT]

    for archetype in ARCHETYPES:
        for register in registers:
            for label in labels:
                batch = generator.generate_batch(archetype, register, label, args.n_per_batch)
                all_examples.extend(batch)
                print(f"{archetype.id}/{register.value}/{label.value}: +{len(batch)}")

    write_jsonl(all_examples, args.out)
    print(f"Wrote {len(all_examples)} synthetic examples to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_generate_synthetic.py -v`
Expected: PASS (4 tests). All tests inject a fake `chat_fn`/call parsing —
no real API key or network call is exercised by the test suite.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/scripts/generate_synthetic.py backend/ml/tests/test_generate_synthetic.py
git commit -m "feat(ml): add GPT-OSS-120B synthetic Hinglish/English scam data generator"
```

---

### Task 6: Combine, dedupe, and split the full dataset

**Files:**
- Create: `backend/ml/scripts/build_dataset.py`
- Create: `backend/ml/tests/test_build_dataset.py`

**Interfaces:**
- Consumes: `Example`, `read_jsonl`, `write_jsonl` from `ml.schema`; `dedupe` from `ml.dedup`.
- Produces: `combine_and_split(input_paths: list[str], out_dir: str, dedupe_threshold: float = 0.92, val_frac: float = 0.1, test_frac: float = 0.1, seed: int = 42, embed_fn=None) -> dict[str, int]` — writes `train.jsonl`/`val.jsonl`/`test.jsonl` under `out_dir`, read by `train.py` (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_build_dataset.py
from __future__ import annotations

import os
import tempfile

from ml.schema import Example, Label, Register, Source, read_jsonl, write_jsonl
from ml.scripts.build_dataset import combine_and_split


def _identity_embed_fn(texts: list[str]) -> list[list[float]]:
    # Each text maps to a distinct one-hot-ish vector so nothing dedupes,
    # keeping this test focused on combine+split, not dedup behavior
    # (dedup itself is covered by test_dedup.py).
    return [[float(i)] for i, _ in enumerate(texts)]


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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_build_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.scripts.build_dataset'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/scripts/build_dataset.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_build_dataset.py -v`
Expected: PASS (2 tests). Both inject `embed_fn` directly, so
`scikit-learn` is the only real dependency exercised (no
`sentence-transformers` model download).

- [ ] **Step 5: Commit**

```bash
git add backend/ml/scripts/build_dataset.py backend/ml/tests/test_build_dataset.py
git commit -m "feat(ml): add dataset combine/dedupe/stratified-split script"
```

---

### Task 7: Hand-curated "known tricky" evaluation set

**Files:**
- Create: `backend/ml/eval/known_tricky.jsonl`
- Create: `backend/ml/tests/test_known_tricky.py`

**Interfaces:**
- Consumes: `read_jsonl` from `ml.schema`.
- Produces: `backend/ml/eval/known_tricky.jsonl` — the held-out regression-gate file read by `evaluate.py` (Task 9). Never included in `train.py`'s training data.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_known_tricky.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_known_tricky.py -v`
Expected: FAIL — `FileNotFoundError` (the jsonl doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

Create the directory and file:

```
# backend/ml/eval/known_tricky.jsonl
{"text": "Bro this strategy literally turned my 50k into 1.5 lakh in three weeks, zero losses guaranteed, the mentor is taking only 10 more students this week so ping me fast for his number", "label": "scam", "source": "curated", "register": "english", "archetype": "guaranteed_returns_paraphrase"}
{"text": "Official notice: your trading account has been selected for the new government-backed wealth scheme, fully compliant with market regulator norms, confirm your PAN and bank details within 24 hours to lock in your slot", "label": "scam", "source": "curated", "register": "english", "archetype": "fake_regulator_paraphrase"}
{"text": "We noticed unusual login activity on your demat, to keep it active please confirm your login id and the code we just sent so our team can verify ownership", "label": "scam", "source": "curated", "register": "english", "archetype": "credential_harvest_paraphrase"}
{"text": "This penny stock is about to explode, insiders are already loading up, get in before tomorrow's announcement and flip it for easy profit, don't tell anyone else", "label": "scam", "source": "curated", "register": "english", "archetype": "pump_dump_paraphrase"}
{"text": "Our private research desk has called 9 out of 10 winning trades this month, join the community before we close registrations tonight, first month free", "label": "scam", "source": "curated", "register": "english", "archetype": "telegram_recruit_paraphrase"}
{"text": "Convert your idle savings into a daily-payout digital asset plan, thousands of investors are already withdrawing profits every single day, early movers get bonus allocation", "label": "scam", "source": "curated", "register": "english", "archetype": "crypto_scheme_paraphrase"}
{"text": "Sir aapka demat account ek special approved scheme ke liye select hua hai, isme bina risk ke fixed monthly income milegi, bas PAN aur bank details confirm kar dijiye 24 hours ke andar warna slot chala jayega", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "fake_regulator_paraphrase"}
{"text": "Aapke account mein suspicious login dikha hai, account active rakhne ke liye apna login id aur abhi jo code aaya hai wo bhej dijiye taaki verify ho sake", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "credential_harvest_paraphrase"}
{"text": "Bhai maine yeh trick try ki aur 15 din mein paisa double ho gaya bina kisi loss ke, mentor sirf 10 log le rahe hain isliye jaldi contact karo", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "guaranteed_returns_paraphrase"}
{"text": "Humara VIP group is mahine 9 out of 10 sahi calls de chuka hai, aaj raat tak hi entry khuli hai, pehla mahina bilkul free hai", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "telegram_recruit_paraphrase"}
{"text": "Yeh chhota stock kal bahut upar jaane wala hai, bade log already kharid rahe hain, kal ki news se pehle le lo warna miss kar doge", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "pump_dump_paraphrase"}
{"text": "Apna padha hua paisa ek daily payout wale digital plan mein daal do, hazaaro log already roz profit nikal rahe hain, jaldi karne walo ko extra bonus milega", "label": "scam", "source": "curated", "register": "hinglish", "archetype": "crypto_scheme_paraphrase"}
{"text": "Your order to buy 10 shares of TCS at market price has been executed. Order ID 48213. View the contract note in your app under Order History.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_broker_alert"}
{"text": "A dividend of Rs 45.60 per share has been credited to your linked bank account for your holdings as of the record date. No action is required from you.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_dividend_notice"}
{"text": "As a SEBI-registered investment adviser, we do not guarantee returns on any recommendation. Please read all scheme-related documents carefully before investing.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_sebi_language"}
{"text": "Your one-time password for logging into your trading account is 482913, valid for 5 minutes. Do not share this code with anyone, including our support team.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_otp_message"}
{"text": "Your margin utilization has crossed 80% of the available limit. Please add funds or reduce positions to avoid a margin call.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_margin_alert"}
{"text": "Your KYC is due for periodic update as per exchange regulations. You can complete this from the Profile section of the app; no payment is required for this process.", "label": "legit", "source": "curated", "register": "english", "archetype": "legit_kyc_reminder"}
{"text": "Aapka order TCS ke 10 shares ke liye market price par execute ho gaya hai. Order ID 48213. Contract note app mein Order History section mein dekh sakte hain.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_broker_alert"}
{"text": "Aapke holdings par record date ke hisaab se Rs 45.60 per share ka dividend aapke linked bank account mein credit ho gaya hai. Iske liye koi action nahi chahiye.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_dividend_notice"}
{"text": "Hum ek SEBI-registered investment adviser hain aur kisi bhi recommendation par guaranteed return ka wada nahi karte. Invest karne se pehle sabhi scheme documents zaroor padhein.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_sebi_language"}
{"text": "Aapke trading account login ke liye OTP 482913 hai, yeh 5 minute ke liye valid hai. Yeh code kisi ke saath, hamari support team ke saath bhi, share na karein.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_otp_message"}
{"text": "Aapka margin usage available limit ka 80% paar kar gaya hai. Margin call se bachne ke liye funds add karein ya positions kam karein.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_margin_alert"}
{"text": "Exchange regulations ke according aapki KYC periodic update ke liye due hai. Isse app ke Profile section se complete kar sakte hain, iske liye koi payment nahi chahiye.", "label": "legit", "source": "curated", "register": "hinglish", "archetype": "legit_kyc_reminder"}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_known_tricky.py -v`
Expected: PASS (24 examples, 12 scam / 12 legit, both registers present).

- [ ] **Step 5: Commit**

```bash
git add backend/ml/eval/known_tricky.jsonl backend/ml/tests/test_known_tricky.py
git commit -m "feat(ml): add hand-curated known-tricky evaluation set"
```

---

### Task 8: MuRIL fine-tuning script

**Files:**
- Create: `backend/ml/train.py`
- Create: `backend/ml/tests/test_train.py`

**Interfaces:**
- Consumes: `train.jsonl`/`val.jsonl` produced by `build_dataset.py` (Task 6).
- Produces: `label2id = {"legit": 0, "scam": 1}`, `id2label`, `build_model_and_tokenizer(model_name: str)`, `load_split(path: str)`, `compute_metrics(eval_pred) -> dict`, `main(args)` — output checkpoint directory consumed by `evaluate.py` (Task 9) and by `backend/app/config.py`'s `transformer_model` setting (Task 10).

Training MuRIL end-to-end takes real GPU time and downloads ~1GB of
weights, so it isn't something to run inside a unit test. This task's
tests exercise the script's pure logic (metrics computation, label
mapping) with a tiny mocked model/tokenizer, and the full training run is
a separate manual/documented invocation.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_train.py
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from ml.train import compute_metrics, id2label, label2id


def test_label_mappings_are_consistent():
    assert label2id == {"legit": 0, "scam": 1}
    assert id2label == {0: "legit", 1: "scam"}


def test_compute_metrics_reports_precision_recall_f1():
    # 4 examples: predictions [scam, scam, legit, legit], labels [scam, legit, legit, scam]
    logits = np.array([[0.1, 0.9], [0.2, 0.8], [0.9, 0.1], [0.8, 0.2]])
    labels = np.array([1, 0, 0, 1])

    metrics = compute_metrics((logits, labels))

    assert set(metrics.keys()) >= {"accuracy", "precision", "recall", "f1"}
    assert metrics["accuracy"] == pytest.approx(0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_train.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.train'` (or
SKIPPED if `torch`/`transformers` aren't installed yet — install
`ml/requirements.txt` first to actually exercise this task).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/train.py
"""Fine-tune MuRIL as a binary scam/legit text classifier.

Run (after backend/ml/requirements.txt is installed and data/processed/
has been produced by build_dataset.py):

    python -m ml.train --train data/processed/train.jsonl \
        --val data/processed/val.jsonl --out models/muril-scam-classifier

MuRIL (google/muril-base-cased) is used instead of an English-only model
because it is trained on Indian languages including transliterated/
code-mixed text, which is what the Hinglish portion of the dataset needs.
"""
from __future__ import annotations

import argparse

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from ml.schema import read_jsonl

MODEL_NAME = "google/muril-base-cased"
label2id = {"legit": 0, "scam": 1}
id2label = {0: "legit", 1: "scam"}


def build_model_and_tokenizer(model_name: str = MODEL_NAME):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=2, label2id=label2id, id2label=id2label,
    )
    return model, tokenizer


def load_split(path: str):
    from datasets import Dataset

    examples = read_jsonl(path)
    return Dataset.from_dict({
        "text": [e.text for e in examples],
        "label": [label2id[e.label.value] for e in examples],
    })


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0,
    )
    return {
        "accuracy": accuracy_score(labels, predictions),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> None:
    from transformers import Trainer, TrainingArguments

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default="data/processed/train.jsonl")
    parser.add_argument("--val", default="data/processed/val.jsonl")
    parser.add_argument("--out", default="models/muril-scam-classifier")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    model, tokenizer = build_model_and_tokenizer()
    train_ds = load_split(args.train)
    val_ds = load_split(args.val)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=256)

    train_ds = train_ds.map(tokenize, batched=True)
    val_ds = val_ds.map(tokenize, batched=True)

    training_args = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"Saved model to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `pip install -r ml/requirements.txt && python -m pytest ml/tests/test_train.py -v`
Expected: PASS (2 tests) if `torch`/`transformers` are installed; SKIPPED
otherwise (via `pytest.importorskip`), which keeps the base test suite
green without requiring the heavy ML deps.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/train.py backend/ml/tests/test_train.py
git commit -m "feat(ml): add MuRIL fine-tuning script for scam/legit text classification"
```

---

### Task 9: Evaluation & promotion gate

**Files:**
- Create: `backend/ml/evaluate.py`
- Create: `backend/ml/tests/test_evaluate.py`

**Interfaces:**
- Consumes: trained model directory (Task 8 output), `known_tricky.jsonl` (Task 7), `label2id`/`id2label` from `ml.train`.
- Produces: `should_promote(new_metrics: dict, baseline_metrics: dict, known_tricky_accuracy: float, min_known_tricky_accuracy: float = 0.85, min_f1_improvement: float = 0.05) -> tuple[bool, str]` — the manual promotion decision function referenced by Task 10's rollout step.

- [ ] **Step 1: Write the failing test**

```python
# backend/ml/tests/test_evaluate.py
from __future__ import annotations

from ml.evaluate import should_promote


def test_promotes_when_both_thresholds_met():
    ok, reason = should_promote(
        new_metrics={"f1": 0.90},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.90,
    )
    assert ok is True


def test_rejects_when_known_tricky_accuracy_too_low():
    ok, reason = should_promote(
        new_metrics={"f1": 0.95},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.70,
    )
    assert ok is False
    assert "known_tricky" in reason


def test_rejects_when_f1_improvement_too_small():
    ok, reason = should_promote(
        new_metrics={"f1": 0.81},
        baseline_metrics={"f1": 0.80},
        known_tricky_accuracy=0.95,
    )
    assert ok is False
    assert "f1" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest ml/tests/test_evaluate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ml.evaluate'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/ml/evaluate.py
"""Regression gate deciding whether a newly trained model should replace
the current default transformer_model in backend/app/config.py.

Run (after training):
    python -m ml.evaluate --model models/muril-scam-classifier \
        --known-tricky eval/known_tricky.jsonl --baseline-f1 <rule-only-f1>
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
    parser.add_argument("--known-tricky", default="eval/known_tricky.jsonl")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest ml/tests/test_evaluate.py -v`
Expected: PASS (3 tests) — these only exercise `should_promote`'s pure
logic, no model loading required.

- [ ] **Step 5: Commit**

```bash
git add backend/ml/evaluate.py backend/ml/tests/test_evaluate.py
git commit -m "feat(ml): add promotion gate comparing new model against baseline + known-tricky set"
```

---

### Task 10: Backend integration — wire the trained model into `text_engine.py`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/engines/text_engine.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_engines.py`

**Interfaces:**
- Consumes: the checkpoint directory produced by `train.py` (Task 8), promoted per `evaluate.py` (Task 9).
- Modifies: `_transformer_score()` label matching so it recognizes the `"scam"`/`"legit"` labels this project's model emits, in addition to the existing generic-model label conventions (`"spam"`, `"label_1"`, `"1"`) — so nothing that currently depends on the generic default breaks if `ENABLE_TRANSFORMERS` is toggled with a different model.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_engines.py — add near the other text-engine tests
def test_transformer_score_recognizes_scam_label(monkeypatch):
    import app.engines.text_engine as text_engine_module

    class _FakeClassifier:
        def __call__(self, text):
            return [{"label": "scam", "score": 0.93}]

    monkeypatch.setattr(text_engine_module, "_get_transformer", lambda: _FakeClassifier())
    monkeypatch.setattr(
        text_engine_module.get_settings().__class__, "enable_transformers",
        property(lambda self: True),
    )

    bundle = TextEngine().analyze(
        Payload(modality=Modality.TEXT, text="Some message long enough to classify")
    )
    signals = {e.signal: e for e in bundle.items}
    assert "transformer_spam" in signals
    assert signals["transformer_spam"].score == 0.93
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/test_engines.py::test_transformer_score_recognizes_scam_label -v`
Expected: FAIL — `_transformer_score`'s current check (`"spam" in label or label in {"label_1", "1"}`) does not match `"scam"`, so no `transformer_spam` evidence is added and the assertion fails.

- [ ] **Step 3: Write minimal implementation**

Modify `_transformer_score` in `backend/app/engines/text_engine.py`:

```python
    def _transformer_score(self, bundle, text):
        clf = _get_transformer()
        if clf is None:
            return
        try:
            out = clf(text[:512])[0]
            label = str(out.get("label", "")).lower()
            conf = float(out.get("score", 0.0))
            if "spam" in label or "scam" in label or label in {"label_1", "1"}:
                bundle.add(
                    "transformer_spam", conf,
                    "Neural classifier flags this as spam/scam-like.",
                    Component.PHISHING, weight=1.1, model_confidence=conf,
                )
        except Exception:  # pragma: no cover
            pass
```

Modify `backend/app/config.py`:

```python
    # Model choices (used only when the matching flag is on)
    transformer_model: str = "./ml/models/muril-scam-classifier"
```

Modify `backend/.env.example`:

```
TRANSFORMER_MODEL=./ml/models/muril-scam-classifier
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/test_engines.py -v`
Expected: PASS (all tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/engines/text_engine.py backend/.env.example backend/tests/test_engines.py
git commit -m "feat: wire trained MuRIL scam classifier into text engine's transformer hook"
```

---

### Task 11: Android — extract testable "meaningful change" logic

**Files:**
- Create: `android/app/src/main/java/com/investwall/app/domain/VerdictChange.kt`
- Create: `android/app/src/test/java/com/investwall/app/domain/VerdictChangeTest.kt`

**Interfaces:**
- Consumes: `TrustReport`, `TrustBand` from `com.investwall.app.domain.model`.
- Produces: `object VerdictChange { fun isMeaningfulChange(local: TrustReport, server: TrustReport): Boolean }` — consumed by `SmsAnalysisWorker` (Task 12) and `ShareViewModel` (Task 13) to decide whether to re-notify/re-emit after the automatic backend escalation.

Note: this project's known constraint (see README §15) is that the
Android APK cannot be built inside this sandboxed environment (Gradle's
loopback selector is blocked). The `./gradlew test` command below must be
run on a real machine or CI — write the test now regardless, since the
logic itself (`isMeaningfulChange`) is plain Kotlin with no Android
framework dependency and no Robolectric/instrumentation needed.

- [ ] **Step 1: Write the failing test**

```kotlin
// android/app/src/test/java/com/investwall/app/domain/VerdictChangeTest.kt
package com.investwall.app.domain

import com.investwall.app.domain.model.TrustBand
import com.investwall.app.domain.model.TrustReport
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VerdictChangeTest {

    private fun report(score: Int, band: TrustBand) = TrustReport(
        id = "1", createdAt = 0L, modality = "text", source = "sms", sender = null,
        filename = null, inputPreview = "text", trustScore = score, band = band,
        confidence = 0.5f, primaryThreat = null, componentScores = emptyMap(),
        explanation = "", llmProvider = "template", evidence = emptyList(),
    )

    @Test
    fun `band change is meaningful`() {
        val local = report(60, TrustBand.POTENTIALLY_MANIPULATED)
        val server = report(20, TrustBand.HIGH_RISK)
        assertTrue(VerdictChange.isMeaningfulChange(local, server))
    }

    @Test
    fun `large score swing within the same band is meaningful`() {
        val local = report(85, TrustBand.HIGHLY_AUTHENTIC)
        val server = report(68, TrustBand.HIGHLY_AUTHENTIC).copy(trustScore = 68)
        // Note: same-band but >=15 point swing still counts as meaningful.
        val serverAdjusted = server.copy(band = TrustBand.HIGHLY_AUTHENTIC)
        assertTrue(VerdictChange.isMeaningfulChange(local, serverAdjusted))
    }

    @Test
    fun `small score change is not meaningful`() {
        val local = report(85, TrustBand.HIGHLY_AUTHENTIC)
        val server = report(80, TrustBand.HIGHLY_AUTHENTIC)
        assertFalse(VerdictChange.isMeaningfulChange(local, server))
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `android/`, on a real machine/CI per the known build constraint): `./gradlew testDebugUnitTest --tests "com.investwall.app.domain.VerdictChangeTest"`
Expected: FAIL to compile — `VerdictChange` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```kotlin
// android/app/src/main/java/com/investwall/app/domain/VerdictChange.kt
package com.investwall.app.domain

import com.investwall.app.domain.model.TrustReport
import kotlin.math.abs

/**
 * Decides whether an automatic backend re-check (deep AI check) produced a
 * result different enough from the on-device result to be worth surfacing
 * again (updated notification / updated UI state).
 */
object VerdictChange {
    private const val MEANINGFUL_SCORE_DELTA = 15

    fun isMeaningfulChange(local: TrustReport, server: TrustReport): Boolean {
        if (local.band != server.band) return true
        return abs(local.trustScore - server.trustScore) >= MEANINGFUL_SCORE_DELTA
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `android/`, on a real machine/CI): `./gradlew testDebugUnitTest --tests "com.investwall.app.domain.VerdictChangeTest"`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/investwall/app/domain/VerdictChange.kt android/app/src/test/java/com/investwall/app/domain/VerdictChangeTest.kt
git commit -m "feat(android): add VerdictChange to detect meaningful score/band changes"
```

---

### Task 12: Android — `SmsAnalysisWorker` auto-escalates to the backend

**Files:**
- Modify: `android/app/src/main/java/com/investwall/app/sms/SmsAnalysisWorker.kt`
- Modify: `android/app/src/main/java/com/investwall/app/notifications/Notifier.kt`

**Interfaces:**
- Consumes: `VerdictChange.isMeaningfulChange` (Task 11), `AnalysisRepository.deepCheck` (existing, `AnalysisRepository.kt:64`).
- Modifies: `Notifier.notifyResult` gains an optional `notificationKey: Int = report.id.hashCode()` parameter so the follow-up (server) notification replaces the first (local) one instead of creating a duplicate.

There is no existing unit test infra covering `SmsAnalysisWorker` itself
(it depends on `WorkManager`/`Context`, which need instrumentation, not
covered by this repo's current test setup) — the testable decision logic
was already extracted into `VerdictChange` in Task 11. This task is
integration wiring; validate it manually per Step 4 below (build target,
not automated test).

- [ ] **Step 1: Modify `Notifier.kt` to accept a stable notification key**

```kotlin
    fun notifyResult(report: TrustReport, sender: String?, notificationKey: Int = report.id.hashCode()) {
        // Only alert when there is something to worry about.
        if (report.band == TrustBand.HIGHLY_AUTHENTIC) return
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) return

        val title = when (report.band) {
            TrustBand.HIGH_RISK -> "High-risk message detected"
            else -> "Potentially manipulated message"
        }
        val text = buildString {
            if (!sender.isNullOrBlank()) append("From $sender · ")
            append("Trust ${report.trustScore}/100. ")
            report.primaryThreat?.let { append(it) }
        }

        val openApp = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(report.explanation))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(openApp)
            .build()

        NotificationManagerCompat.from(context).notify(notificationKey, notification)
    }
```

(Only the method signature and the final `.notify(...)` call change —
everything else in `Notifier.kt` stays as-is.)

- [ ] **Step 2: Modify `SmsAnalysisWorker.kt` to auto-escalate after the local result**

```kotlin
package com.investwall.app.sms

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.investwall.app.data.SettingsRepository
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.VerdictChange
import com.investwall.app.notifications.Notifier
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

/**
 * Analyses a received SMS in the background and raises a notification when the
 * result is risky. Respects the user's "scan incoming SMS" preference.
 *
 * The on-device rule engine screens the message first so a notification can
 * fire instantly even offline; the backend's trained model is then called
 * automatically (no user action) to refine the verdict, and the notification
 * is updated in place if the refined result changes meaningfully.
 */
@HiltWorker
class SmsAnalysisWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val repository: AnalysisRepository,
    private val settings: SettingsRepository,
    private val notifier: Notifier,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        if (!settings.smsScanEnabled.first()) return Result.success()

        val body = inputData.getString(KEY_BODY) ?: return Result.success()
        val sender = inputData.getString(KEY_SENDER)

        val localReport = try {
            val report = repository.analyzeTextLocally(text = body, source = "sms", sender = sender)
            val notificationKey = report.id.hashCode()
            notifier.notifyResult(report, sender, notificationKey)
            report to notificationKey
        } catch (e: Exception) {
            return Result.retry()
        }

        val (report, notificationKey) = localReport
        // Automatic backend escalation — no button, matches the product
        // requirement that every message is checked, not just ones the user
        // opts into. Failures here are swallowed rather than retried: the
        // local result + notification already succeeded, and repeatedly
        // retrying the whole worker would just re-run the local analysis
        // and hammer a possibly-down backend.
        try {
            val serverReport = repository.deepCheck(report)
            if (VerdictChange.isMeaningfulChange(report, serverReport)) {
                notifier.notifyResult(serverReport, sender, notificationKey)
            }
        } catch (e: Exception) {
            // Backend unreachable or escalation failed — fall back to the
            // on-device-only result, which the user has already seen.
        }

        return Result.success()
    }

    companion object {
        const val KEY_BODY = "body"
        const val KEY_SENDER = "sender"
    }
}
```

- [ ] **Step 3: Manual verification (on a real machine, per repo build constraint)**

1. Run the backend locally (`uvicorn app.main:app --reload`).
2. Build and install the debug APK (`./gradlew installDebug`) on an
   emulator/device with the backend URL configured in Settings.
3. Enable "Scan incoming SMS" in Settings.
4. Send a test SMS containing scam language to the device.
5. Confirm a notification appears immediately (local rule-engine result).
6. Confirm the notification updates in place (same notification, not a
   duplicate) if the backend's verdict differs meaningfully — check
   Logcat for the `deepCheck` network call completing.
7. Turn off Wi-Fi/data, repeat with a new SMS: confirm the local
   notification still appears and no crash/retry loop occurs.

- [ ] **Step 4: Commit**

```bash
git add android/app/src/main/java/com/investwall/app/sms/SmsAnalysisWorker.kt android/app/src/main/java/com/investwall/app/notifications/Notifier.kt
git commit -m "feat(android): auto-escalate SMS analysis to backend, update notification in place"
```

---

### Task 13: Android — `ShareViewModel` auto-escalates shared text

**Files:**
- Modify: `android/app/src/main/java/com/investwall/app/share/ShareViewModel.kt`

**Interfaces:**
- Consumes: `VerdictChange.isMeaningfulChange` (Task 11), `AnalysisRepository.deepCheck` (existing).
- Modifies: `analyzeText` now automatically triggers a background `deepCheck` after the local result, updating `state` if the verdict changes — no button in the UI needed for this path either.

- [ ] **Step 1: Modify `ShareViewModel.kt`**

```kotlin
package com.investwall.app.share

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investwall.app.data.repository.AnalysisRepository
import com.investwall.app.domain.VerdictChange
import com.investwall.app.domain.model.TrustReport
import com.investwall.app.ui.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException
import javax.inject.Inject

/** Drives analysis for content shared into the app via Android Share Intent. */
@HiltViewModel
class ShareViewModel @Inject constructor(
    private val repository: AnalysisRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<TrustReport>>(UiState.Loading)
    val state: StateFlow<UiState<TrustReport>> = _state.asStateFlow()

    private var started = false

    fun analyzeText(text: String, source: String?) {
        if (started) return
        started = true
        // Instant on-device result first, then automatically (no button)
        // escalate to the backend's trained model and refine the result if
        // it changes meaningfully — matches the SMS auto-escalation flow.
        viewModelScope.launch {
            _state.value = UiState.Loading
            val localReport = try {
                repository.analyzeTextLocally(text, source ?: "shared")
            } catch (e: Exception) {
                _state.value = UiState.Error(e.message ?: "Analysis failed.")
                return@launch
            }
            _state.value = UiState.Success(localReport)

            try {
                val serverReport = repository.deepCheck(localReport)
                if (VerdictChange.isMeaningfulChange(localReport, serverReport)) {
                    _state.value = UiState.Success(serverReport)
                }
            } catch (e: IOException) {
                // Backend unreachable — keep showing the on-device result.
            } catch (e: Exception) {
                // Escalation failed for another reason — keep the on-device result.
            }
        }
    }

    fun analyzeUri(uri: Uri, source: String?) {
        if (started) return
        started = true
        analyze { repository.analyzeFile(uri, source ?: "shared") }
    }

    private fun analyze(block: suspend () -> TrustReport) {
        _state.value = UiState.Loading
        viewModelScope.launch {
            _state.value = try {
                UiState.Success(block())
            } catch (e: IOException) {
                UiState.Error("Can't reach the InvestWall backend. Open the app → Settings to set the server URL.")
            } catch (e: Exception) {
                UiState.Error(e.message ?: "Analysis failed.")
            }
        }
    }
}
```

- [ ] **Step 2: Manual verification (on a real machine, per repo build constraint)**

1. Share a scam-like text snippet from another app (e.g. Messages) into
   InvestWall.
2. Confirm the report screen shows the instant local result first.
3. Confirm the result updates automatically (no button tap) shortly after,
   if the backend's verdict differs meaningfully.
4. Repeat with Wi-Fi/data off: confirm the local result stays displayed
   with no error shown to the user (escalation fails silently).

- [ ] **Step 3: Commit**

```bash
git add android/app/src/main/java/com/investwall/app/share/ShareViewModel.kt
git commit -m "feat(android): auto-escalate shared text analysis to backend"
```

---

### Task 14: Update README privacy-model section

**Files:**
- Modify: `README.md` (§11b "Privacy model — hybrid on-device + server")

**Interfaces:** None (documentation only).

- [ ] **Step 1: Update the privacy section**

Replace the current §11b content (the table and bullets describing
opt-in-only backend analysis for text) with:

```markdown
## 11b. Privacy model — hybrid on-device + automatic backend check

InvestWall runs the on-device rule engine on every message first, for an
instant, private, offline-capable result — then **automatically** (no
button, no opt-in) sends the same text to your configured backend so the
trained scam/phishing model can refine the verdict. This is a deliberate
tradeoff for detection quality: earlier versions of this document
described text as staying on-device by default, but automatic backend
checking means every SMS and shared text now leaves the device by
default.

| Content | Where it's analyzed | Leaves the device? |
|---|---|---|
| **Typed text / SMS / shared text** | On-device rule engine (instant) **then** automatically re-checked by the backend's trained model | ✅ Yes, automatically, in the background |
| **Files** (image / video / audio / PDF) | Backend (needs big models) | ✅ Yes, on pick/share |

Privacy levers that still apply:

- **Self-hostable backend**: the server URL is configurable, so a
  privacy-conscious user (or a broker/SEBI) runs their **own** backend —
  content only ever goes to a server they control, never a third party.
- **No-retention mode**: set `STORE_RAW_CONTENT=0` on the backend so it
  persists only scores/evidence/metadata, never the raw text or sender.
- **Offline fallback**: if the backend is unreachable, the on-device rule
  result is what the user sees — analysis is never blocked on network
  availability, only refined by it.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update privacy-model section for automatic backend text analysis"
```

---

## Self-Review Notes

- **Spec coverage:** every section of the design doc has a task — quote
  bank (Task 2), public data (Task 3), dedup (Task 4), synthetic
  generation (Task 5), combine/split (Task 6), known-tricky eval (Task
  7), training (Task 8), promotion gate (Task 9), backend wiring (Task
  10), Android auto-escalation for SMS (Task 12) and share (Task 13),
  and the README privacy update (Task 14). Task 11 was added during
  planning to keep the Android escalation logic unit-testable, which the
  spec implied but didn't name explicitly.
- **Type consistency checked:** `Example`/`Label`/`Register`/`Source`
  (Task 1) are used with identical field names across Tasks 3–9;
  `label2id`/`id2label` (Task 8) match what `evaluate.py` (Task 9) and
  `_transformer_score` (Task 10) expect; `VerdictChange.isMeaningfulChange`
  (Task 11) has one signature used identically in Tasks 12 and 13.
- **No placeholders:** the only forward-references are the two already
  flagged as "Open Items" in the design doc (GPT-OSS-120B provider
  base-url, and expanding `ARCHETYPES`/`SCAM_QUOTE_BANK` past their
  starter sizes) — both are concrete, actionable, scoped steps, not vague
  instructions.
