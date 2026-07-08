# Text Scam/Phishing Detection: ML Model Design

Status: Approved (pending user review of this document)
Date: 2026-07-08

## Background

InvestWall's text engine ([backend/app/engines/text_engine.py](../../../backend/app/engines/text_engine.py))
currently detects scams/phishing purely via rule-based regex patterns
([backend/app/knowledge/phishing_rules.py](../../../backend/app/knowledge/phishing_rules.py)) and a
stylometric heuristic. This is broadly unreliable in practice — it misses
reworded/paraphrased scams the regexes weren't written for, and produces
false positives on legitimate messages that share surface vocabulary with
scam patterns.

The codebase already has an unused hook for a trained model:
`enable_transformers` / `transformer_model` in
[backend/app/config.py](../../../backend/app/config.py), consumed by
`_transformer_score()` in `text_engine.py`. This project fills that hook
with a real, trained classifier instead of the currently-configured generic
SMS-spam model.

This is the first of the six detection engines to get a trained model
(per the README's Phase 3 roadmap); image/video/audio are explicitly
out of scope for this project and will follow the same pattern later.

## Goals

- Materially reduce false negatives/positives in text scam/phishing detection
  relative to the current rule-only engine.
- Detect scams written in Hinglish (Hindi-English code-mixed, Roman script)
  as well as English, since that's how a large share of real Indian
  SMS/WhatsApp scam traffic is actually written.
- Keep the rule engine's evidence/reasons intact for explainability — the
  trained model augments the phishing component score, it does not replace
  the rule engine or the explanation pipeline.
- Make the model available automatically for every incoming SMS and
  shared text, with no user-initiated action required.

## Non-goals

- Image, video, and audio engine training (future, separate projects).
- On-device (Android) model deployment — this model is backend-only. The
  Android on-device rule engine is unchanged and continues to produce the
  instant local score.
- Building a labeled dataset from real user-reported messages (no such data
  exists yet) — this project bootstraps from public datasets plus
  synthetic generation.

## Privacy model change (explicit, not incidental)

Today, per the README's "hybrid privacy model," text/SMS is analyzed
on-device by default and only sent to the backend when the user taps
"Run deep AI check." **This project removes that opt-in gate for
automatic SMS/share-intent analysis**: every incoming SMS and shared text
will be sent to the backend automatically, with no button press, so the
trained model can score it. This is a deliberate product decision made in
this design (not a bug) — the README's privacy section will be updated to
reflect it honestly rather than leave the stale "never leaves the device
by default" claim in place.

The on-device rule engine still runs first and instantly, so the user
sees a result even if the network is slow or briefly unavailable; the
backend call happens in the background afterward and refines/updates the
notification if the verdict changes.

## Data Pipeline

### Real scam-quote / keyword bank

Curate a bank of real scam keywords and quoted excerpts from public
sources: SEBI/RBI investor-alert pages, cybercrime.gov.in advisories, and
news coverage of specific reported frauds. This bank serves two purposes:

1. Expands `RISKY_KEYWORDS` and the rule patterns in `phishing_rules.py`
   directly (benefits the rule engine independent of ML).
2. Provides grounding few-shot seed material for synthetic generation, so
   generated examples stay anchored to real scam phrasing rather than
   drifting into generic, unrealistic LLM-invented text.

### Public datasets (real-world base)

- **SMS Spam Collection** (UCI, ~5.5k messages, ham/spam) — general spam
  patterns and a pool of genuine "ham" text for the legit class.
- **Nazario phishing corpus** / Kaggle phishing-email datasets — email-style
  phishing structure and language.
- **Enron email subset** (legit business email) — additional "legit but
  formal/urgent" hard negatives, so the model doesn't learn "urgent = bad."

### Synthetic generation (closes the India/securities/Hinglish domain gap)

Generator: **GPT-OSS-120B via API** (user-supplied key; specific inference
provider/base-url to be confirmed at implementation time).

Expand from the current 18 rule patterns in `phishing_rules.py` to
**~40–60 scam archetypes**, covering additional scam vehicles not yet
encoded as rules (crypto-linked schemes, fake IPO allotment, F&O tip
scams, penny-stock pump-and-dump variants, fake demat/KYC suspension,
cloned-advisor impersonation, etc.).

For each archetype, generate variants across three registers:

- **English** — paraphrased, varied length/channel (SMS/WhatsApp/email),
  varied phrasing that conveys the same scam without matching the literal
  regex (this is the actual generalization gap rules can't cover).
- **Hinglish (Roman-script code-mixed)** — realistic Hindi-English mixing
  as actually typed on Indian WhatsApp/SMS (e.g. "aapka demat account
  block ho jayega, abhi verify kare"), at varying code-mixing intensity.
- **Mixed/varied register** — combinations of the above plus typos,
  abbreviations, and informal punctuation patterns seen in real forwards.

Every generated batch is seeded with real quotes from the keyword/quote
bank for grounding.

For every scam archetype, generate a **matched batch of legit
counterparts** in the same registers (English and Hinglish), including
ones that use the same hot vocabulary (SEBI, guaranteed, dividend, KYC)
in a genuine, non-scam context — e.g. real brokerage order/margin alerts,
authentic SEBI-circular-style text, genuine OTP/dividend-credit messages,
and Hinglish versions of legitimate bank/broker notifications. This
prevents the model from learning "mentions SEBI/Hindi = risk" instead of
actual scam semantics.

### Target scale

**~50k–80k combined examples** (public + synthetic English + synthetic
Hinglish), roughly balanced between scam and legit classes, with the
synthetic/domain-specific subset intentionally oversampled relative to
its natural rarity in public data, since that's the accuracy gap that
matters most here.

### Cleaning and splitting

- Deduplicate near-duplicates via embedding-similarity threshold (not just
  exact-text hashing, since paraphrases are the point).
- Stratified train/val/test split.
- A small **hand-curated "known tricky" eval set** — paraphrased scams,
  tricky-but-legit messages, and Hinglish tricky cases — is built
  separately and held out entirely from training. This is the real
  accuracy gate, since public/synthetic data alone can't validate
  real-world generalization.

### Pipeline layout

A new `backend/ml/` directory, separate from the runtime `app/`:

```
backend/ml/
├── data/
│   ├── raw/            # downloaded public datasets (gitignored)
│   └── synthetic/       # LLM-generated JSONL (checked into git — text only)
├── scripts/
│   ├── fetch_public_datasets.py
│   ├── generate_synthetic.py   # archetype + register loop, seeded by quote bank
│   └── build_dataset.py        # combine, dedupe, stratified split
├── train.py                     # HF Trainer fine-tuning script
└── eval/
    └── known_tricky.jsonl       # hand-curated held-out eval set
```

## Model & Training

**Backbone: MuRIL** (Google's model trained specifically on Indian
languages including transliterated/code-mixed text), chosen over
DeBERTa-v3-small because DeBERTa's vocabulary is trained almost entirely
on English text and would tokenize Hinglish poorly — splitting Hindi
words (in Roman script) into low-signal sub-tokens. MuRIL is ~236M
parameters, which is trivial for backend-only serving (no on-device
constraint applies here).

Fine-tune MuRIL as a binary sequence classifier (scam/phishing=1 vs
legit=0) using HuggingFace `Trainer`, on a local GPU. This matches the
label interpretation `_transformer_score()` already expects (`"spam" in
label` → phishing evidence).

## Evaluation & Success Criteria

- Precision/recall/F1 on the held-out stratified test split.
- Extra weight on **false-negative rate specifically on the synthetic
  SEBI-themed subset and the Hinglish subset** — these are the domains
  public benchmarks can't validate and where the current rule engine is
  known to be weak.
- Regression gate before promoting the model to default: it must not
  regress any of the existing 20 backend pytest cases
  ([backend/tests/](../../../backend/tests/)), and must outperform the
  current rule-only baseline on the hand-curated `known_tricky.jsonl` set.

## Backend Integration

- No API contract changes. `/analyze` already returns
  transformer-influenced scores when `enable_transformers` is on.
- Once the trained model clears evaluation, set `ENABLE_TRANSFORMERS=1` as
  the default and point `transformer_model` at the new MuRIL checkpoint
  (replacing the current generic `mrm8488/bert-tiny-finetuned-sms-spam-detection`
  default).
- The rule engine and stylometry heuristic keep running unchanged —
  `_transformer_score()` adds an additional evidence item to the existing
  bundle; it does not replace rule-based reasons, preserving the LLM
  explainer's ability to cite concrete reasons.

## Android Integration

`SmsAnalysisWorker`
([android/.../sms/SmsAnalysisWorker.kt](../../../android/app/src/main/java/com/investwall/app/sms/SmsAnalysisWorker.kt))
changes from local-only to local-then-auto-escalate:

1. Run `analyzeTextLocally()` first (unchanged) — instant on-device rule
   score, notification fires immediately.
2. Automatically call the existing `deepCheck()` path in
   [AnalysisRepository.kt](../../../android/app/src/main/java/com/investwall/app/data/repository/AnalysisRepository.kt)
   in the background — no button, no user action.
3. If the backend result changes the verdict meaningfully (e.g. band
   changes, or score moves across a threshold), update the stored report
   and refresh/re-issue the notification.
4. If the backend is unreachable, fall back to the on-device-only result
   via the existing `Result.retry()` / WorkManager retry pattern, rather
   than blocking the user or failing the whole flow.

The same auto-escalation applies to the Share-intent text flow.

## Documentation Updates

- README §11b ("Privacy model — hybrid on-device + server") gets updated
  to state that automatic SMS/text analysis now also calls the backend by
  default, rather than claiming text never leaves the device by default.
  The self-hostable-backend and no-retention-mode mitigations remain valid
  and should be emphasized as the privacy levers that still apply.

## Open Items for Implementation Time

- Which provider serves the user's GPT-OSS-120B API key (Groq / Together /
  Fireworks / OpenRouter / etc.) — determines the base URL and rate limits
  used in `generate_synthetic.py`. Not required to finalize this design.
- Exact list of ~40–60 scam archetypes to generate — to be enumerated as
  part of implementation, using the existing 18 rules in
  `phishing_rules.py` as the starting checklist.
