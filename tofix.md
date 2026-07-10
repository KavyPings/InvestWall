# InvestWall — To Fix

Findings from the review of the ML pipeline (`backend/ml/`), `scam_quotes`, and
their wiring into detection. The ML work is genuinely good and on-purpose, but
the improvements currently bypass the default on-device path. Fix later.

_Reviewed: 2026-07-10. Status: all 22 app tests + 35 ML tests pass; pipeline sound._

---

## Context (why these matter)

Rule-only baseline measured on the 24-case hard set (`ml/eval/known_tricky.jsonl`):
- **Recall 0.08** — catches only **1 of 12** paraphrased scams; misses nearly all
  Hinglish ones (rules only match literal English keywords).
- **False-positives on legit SEBI disclaimers** — "we do *not* guarantee returns"
  trips the guaranteed-returns regex.

The trained **MuRIL** model targets exactly this, but only on the server path.

---

## Priority 1 — On-device default path doesn't benefit (biggest issue)

Text / SMS / shared-text default to the **Kotlin** `LocalAnalyzer`
(`android/app/src/main/java/com/investwall/app/local/LocalKnowledge.kt`), which
has its own smaller hardcoded keyword list. It does **not** include the new
`KEYWORD_ADDITIONS` from `backend/app/knowledge/scam_quotes.py` (digital arrest,
task-wallet, dabba trading, pig-butchering, KYC-freeze, etc.) and cannot run MuRIL.

Since SMS + typed text run on-device by default (privacy), **most real usage hits
the weakest engine**. ML gains only apply on the opt-in "Deep AI check" or file
analysis.

**Fix options:**
- [ ] Port `KEYWORD_ADDITIONS` + new archetype patterns into Kotlin `LocalKnowledge`.
- [ ] Auto-suggest (or auto-run) a Deep AI check when an on-device result is
      borderline / risky.
- [ ] (Later, heavier) ship a distilled/quantized on-device model (TFLite/ONNX).

---

## Priority 2 — MuRIL default  ✅ DONE (2026-07-10)

- `config.py` now defaults `transformer_model=./ml/models/muril-scam-classifier`
  with `transformer_fallback_model` (tiny SMS model) — loader uses MuRIL if the
  weights exist, else auto-falls back so transformers still work out of the box.
- `ENABLE_TRANSFORMERS`/`WHISPER`/`IMAGE_MODEL` now default **ON**.
- Still open: [ ] train + place the MuRIL weights (`ml/models/` is gitignored and
  currently empty on this machine) so the model actually loads;
  [ ] verify `/health` → `transformer_loaded: true`.

---

## False positives fixed (2026-07-10)

- ✅ **Bare regulator mention flagged as impersonation.** "sebi my goat" scored 55
  ("Unverified Authenticity") because `_CLAIM_RE` / `claimAuthorityRegex` matched
  the bare word "sebi". Rewrote both (backend `authenticity_engine.py` + on-device
  `LocalKnowledge.kt`) to require actual authority-claim context ("official SEBI
  circular", "SEBI approved", "registered by SEBI"). "sebi my goat" → 88 now.
- ✅ **Legit screenshots scored 63.** `missing_exif` + `ela_uniform` fire on every
  screenshot (no EXIF, uniform ELA). Lowered their weights AND added a
  **model-override**: when the AI-image model is confident the image is real, the
  noisy heuristics are pruned. Genuine SEBI-doc screenshot → 88 now.

## Priority 3 — Legit-disclaimer false positive (both rule engines)

`FINANCIAL_SCAM_RULES` guaranteed-returns regex matches negated/legit text:
"we do **not** guarantee returns" → flagged as scam. Present in **both**
`backend/app/knowledge/phishing_rules.py` and Kotlin `LocalKnowledge.kt`.
ML fixes it server-side only.

**Fix:**
- [ ] Add a negation guard (e.g. skip when preceded by "do not / does not / never
      guarantee", or when SEBI-disclaimer language is present) in both rule sets.

---

## Priority 4 — Verify the trained model's real accuracy

Weights are gitignored, so the pipeline is sound but actual numbers are unverified.

**Fix:**
- [ ] Run the promotion gate and record numbers:
      `python -m ml.evaluate --model ml/models/muril-scam-classifier \
        --test ml/data/processed/test.jsonl --known-tricky ml/eval/known_tricky.jsonl`
- [ ] Confirm it beats the rule baseline by ≥0.05 F1 AND ≥0.85 on known_tricky.

---

## Notes / lower priority

- [ ] Synthetic data is LLM-generated (GPT-OSS-120B via Bedrock); label noise is
      possible. Hard-negative labeling (e.g. a legit customs message under the
      `digital_arrest_intro` archetype) looked intentional and correct on spot-check,
      but consider a small manual audit of a synthetic sample.
- ✅ Image model now does **face-detect → crop → deepfake model** (recall on
      faces-in-scenes went 0% → ~92%) + a general **AI-image model**
      (`Organika/sdxl-detector`) for non-face synthetic content, with abstention
      when no face is found and confidence-tiered weighting.
- ✅ **Video** now runs the same face-crop→deepfake model over sampled frames.
- ⚠️ Deepfake model has a **false-positive tail on real faces** (~33% ≥0.7 on
      re-cropped faces) due to Haar crop alignment ≠ model training alignment.
      Mitigated with conservative thresholds (strong flag only ≥0.8) + fusion.
      To really fix: better face aligner (RetinaFace/MTCNN) or fine-tune the
      detector on Haar-style crops. [ ]
- [ ] **Audio** still heuristics-only — wire AASIST/RawNet2 (spoof) + the
      Whisper→transcript path is enabled but needs `faster-whisper` installed.

---

## Summary

The ML changes are useful, correct, well-engineered, and on-purpose — they upgrade
the **server / deep-check** path. The **default private path** (where most SMS/text
lands) is unchanged and still weak. Priorities 1 + 3 are the cheapest ways to turn
this ML work into better detection for real users.
