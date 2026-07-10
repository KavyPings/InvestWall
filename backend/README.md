# InvestWall — Backend AI Pipeline

**AI-driven detection of synthetic media & phishing attacks for retail investors.**

This is the backend "brain" from the PRD (§7/§9/§11): incoming content is routed
by modality, analysed by six specialised detection engines, fused into a single
explainable **Trust Score (0–100)**, and turned into human-readable reasoning by a
pluggable LLM layer. The Android app (Phase 2) consumes this REST API.

```
POST /analyze | /analyze/file
   → Content Router → Text/Image/Video/Audio engine(s)
   → Phishing + Authenticity engines
   → Evidence Fusion (weighted) → LLM explanation → Trust Score → stored report
```

## Design principles

- **Functional-MVP fidelity.** Every engine returns *genuinely computed* results
  using feasible libraries (spaCy, OpenCV, Pillow, NumPy, librosa, dnspython,
  rule engines). Heavyweight models (DeepFakeBench, AASIST, DeBERTa, ViT, Whisper)
  drop in behind the same engine interfaces via env flags — no redesign needed.
- **Boots with base deps + no network.** Heavy/optional/network features are
  lazy-loaded and flag-gated; the service degrades gracefully (SQLite instead of
  Postgres, in-memory cache instead of Redis, OpenCV instead of system FFmpeg,
  template explainer instead of an LLM server).
- **Explainable & modular.** The LLM explains structured evidence — it never
  performs detection (tech-stack §10). Each detector is independently upgradeable.

## The six engines (PRD §6)

| # | Engine | What it computes |
|---|--------|------------------|
| 1 | **Text** | spaCy tokenize/NER, stylometric AI-likelihood, rule-based scam/phishing/urgency scoring, optional transformer classifier |
| 2 | **Image** | EXIF/metadata anomalies, Error-Level-Analysis, FFT/noise residual, OpenCV face detection + over-symmetry, AI watermark scan |
| 3 | **Video** | OpenCV frame sampling → per-frame forensics, temporal consistency, blink-rate & over-smoothing heuristics |
| 4 | **Audio** | librosa spectral flatness / MFCC variance / ZCR heuristics for synthetic voice; optional Whisper STT → transcript scam analysis |
| 5 | **Phishing** | URL extraction, shorteners, raw-IP links, look-alike/typosquat brand domains, suspicious TLDs, sender impersonation |
| 6 | **Authenticity** | Official-domain verification (SEBI/NSE/BSE…), SPF/DMARC DNS checks, claimed-vs-verified alignment |

## Trust Score (PRD §8)

Weighted fusion of component risk: **AI 30% · Phishing 25% · Source 15% ·
Authenticity 20% · Metadata 10%**, renormalised over the components present.
Bands: **≥75 Highly Authentic · 40–74 Potentially Manipulated · <40 High Risk**.

## Quick start (local, Windows / macOS / Linux)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm      # optional but recommended
cp .env.example .env                          # optional; defaults are fine

uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> for interactive Swagger UI.

### Try it

```bash
# High-risk scam (PRD Example 1)
curl -s http://localhost:8000/analyze -H "Content-Type: application/json" \
  -d '{"text":"URGENT! SEBI approved GUARANTEED 40% monthly returns. Verify your demat account at http://bit.ly/sebi-x now!!!","source":"whatsapp"}'

# Legitimate official communication
curl -s http://localhost:8000/analyze -H "Content-Type: application/json" \
  -d '{"text":"Please find the official SEBI circular for Q3.","sender":"circulars@sebi.gov.in","source":"email"}'

# File (image/video/audio/pdf/docx)
curl -s -F "file=@photo.jpg" -F "source=gallery" http://localhost:8000/analyze/file
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/health` | Liveness + which optional engines/models are active |
| POST | `/analyze` | `{text, source?, sender?}` → TrustReport |
| POST | `/analyze/file` | multipart `file` (+ `source?`, `sender?`) → TrustReport |
| GET  | `/history?limit=&offset=` | Recent stored reports |
| GET  | `/report/{id}` | Full stored report |

**TrustReport** fields: `id, created_at, modality, trust_score, band, band_label,
band_color, confidence, primary_threat, component_scores{ai,phishing,source,
authenticity,metadata}, evidence[]{signal,component,score,reason}, explanation,
llm_provider, extras`.

## Models & feature flags

All models install from the single `requirements.txt` and are **ON by default**
(each lazy-loads and degrades to rules/heuristics if it can't load). Flip flags in
`.env`:

| Flag (default) | Effect |
|------|--------|
| `ENABLE_TRANSFORMERS=1` | Neural text scam classifier (`TRANSFORMER_MODEL`, falls back to `TRANSFORMER_FALLBACK_MODEL`) |
| `ENABLE_IMAGE_MODEL=1` | Deepfake model on cropped faces (`IMAGE_MODEL`) + general AI-image model (`IMAGE_AI_MODEL`); also runs on video frames |
| `ENABLE_WHISPER=1` | Audio speech-to-text → transcript scam analysis (`WHISPER_MODEL`) |
| `ENABLE_QR=0` | QR decoding in images/PDFs (needs pyzbar + zbar) |
| `ENABLE_DNS=1` | Live SPF/DMARC lookups |
| `STORE_RAW_CONTENT=1` | Set `0` to persist only scores/evidence, never raw text/sender |
| `LLM_PROVIDER=template` | `ollama` (local) or `hosted` for LLM prose |

`GET /health` reports each model's load state (`transformer_loaded`,
`image_model_loaded`, `image_ai_model_loaded`). First request after enabling a
model is slow while weights download/load, then cached. A GPU helps for
image/video throughput. The Android app calls the backend only for the opt-in
**deep AI check** and **file analysis** — text/SMS are screened on-device.

> `backend/ml/requirements.txt` is a **separate** offline pipeline for *retraining*
> the text model — not needed to run the app.

## Tests

```bash
pytest          # runs fully offline against a temp SQLite DB
```

## Deployment (tech-stack §13)

```bash
docker compose up --build       # api + postgres + redis + nginx (gateway :8080)
```

The compose stack builds the API image (installing `requirements.txt`, which
includes the models, and baking the spaCy model), provisions Postgres + Redis,
and fronts everything with Nginx.

## Android integration (Phase 2)

The Kotlin/Compose app (MVVM · Hilt · Retrofit · Room · WorkManager · SMS
BroadcastReceiver · Share Intent · Google OAuth) will call `/analyze` &
`/analyze/file`, render the Trust Score + evidence, and mirror reports into a Room
cache matching the `TrustReport` schema above.
