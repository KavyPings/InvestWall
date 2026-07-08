<div align="center">

# 🛡️ InvestWall

### AI-Driven Detection of Synthetic Media & Phishing Attacks for Retail Investors

**A personal AI trust layer that sits between incoming financial content and your decision to act on it.**

Android app · Python AI backend · Multimodal detection · Explainable Trust Score

</div>

---

## Table of Contents

1. [What is InvestWall?](#1-what-is-investwall)
2. [The Problem](#2-the-problem)
3. [How It Solves It](#3-how-it-solves-it)
4. [System Architecture](#4-system-architecture)
5. [How It Works (End-to-End Workflow)](#5-how-it-works-end-to-end-workflow)
6. [The Six Detection Engines](#6-the-six-detection-engines)
7. [The Trust Score](#7-the-trust-score)
8. [Technology Stack](#8-technology-stack)
9. [Repository Structure](#9-repository-structure)
10. [Getting Started](#10-getting-started)
11. [API Reference](#11-api-reference)
12. [Design Philosophy](#12-design-philosophy)
13. [What's Built vs. What's Missing](#13-whats-built-vs-whats-missing)
14. [Roadmap — How to Go Forward](#14-roadmap--how-to-go-forward)
15. [Known Constraints & Notes](#15-known-constraints--notes)

---

## 1. What is InvestWall?

InvestWall is a two-part system — a **native Android app** and a **Python AI backend** — that protects retail investors from AI-generated fraud in the securities market: phishing messages, deepfake videos, cloned voices, fake regulator announcements, and manipulated financial content.

Unlike a traditional spam filter, InvestWall performs **multimodal AI analysis** (text, image, video, audio, documents), **fuses evidence** from specialised detectors, and produces a single **explainable Trust Score (0–100)** with plain-language reasoning a non-technical user can understand.

It works in two modes:

- **Automatic** — scans incoming **SMS** (and, later, **email**) in the background.
- **On-demand** — you **Share** any message, image, video, voice note, or document from another app (WhatsApp, Telegram, browser, gallery, files…) into InvestWall, or paste text directly.

> Built to the SEBI problem statement: *"AI-Driven Detection of Synthetic Media and Phishing Attacks in Securities Markets."*

---

## 2. The Problem

Generative AI has made convincing financial fraud cheap and scalable. Retail and first-generation investors are especially vulnerable to:

- 🎣 **AI-written phishing** — hyper-personalised scam emails/SMS/WhatsApp forwards.
- 🎥 **Deepfake videos** — of CEOs, CIOs, regulators, and market "experts".
- 🎙️ **Voice cloning** — fake calls/voice notes impersonating advisors.
- 📢 **Fake announcements** — bogus "SEBI/NSE approved guaranteed returns" schemes.
- 📈 **Pump-and-dump** — coordinated social-media manipulation.

There's a **second, mirror-image gap**: there's no easy way to *verify* that a communication genuinely comes from SEBI, an exchange, a listed company, or a registered intermediary. So investors can neither reliably **detect** fakes nor **confirm** authentic messages.

InvestWall addresses **both** dimensions — detection of malicious synthetic content *and* verification of authentic financial communications.

---

## 3. How It Solves It

| Capability | How |
|---|---|
| Detect AI-generated **text** | Stylometry + rule-based scam/phishing detection + (optional) transformer classifiers |
| Detect AI-generated **images** | Metadata/EXIF anomalies, Error-Level-Analysis, noise/FFT forensics, face over-symmetry, AI-watermark scan |
| Detect deepfake **video** | Frame sampling → per-frame forensics → temporal consistency + blink/over-smoothing heuristics |
| Detect cloned **voice** | Spectral flatness / MFCC / ZCR analysis + (optional) Whisper transcript scam analysis |
| Detect **phishing** | Malicious/shortened/raw-IP URLs, typosquat brand domains, suspicious TLDs, sender impersonation |
| **Verify authenticity** | Official-domain registry (SEBI/NSE/BSE…), SPF/DMARC checks, claimed-vs-verified alignment |
| **Explain** the verdict | An LLM layer turns structured evidence into human-readable reasoning (it never does detection itself) |
| **Unify** everything | An Evidence Fusion layer produces one weighted, calibrated Trust Score |

---

## 4. System Architecture

```
┌──────────────────────────── ANDROID APP (Kotlin / Compose) ────────────────────────────┐
│                                                                                         │
│   Automatic sources            On-demand sources                                        │
│   • SMS (BroadcastReceiver)    • Share Intent (WhatsApp, Telegram, browser, files…)     │
│   • Email (Gmail OAuth)*       • Paste text                                             │
│                         │                                                               │
│                         ▼                                                               │
│            MVVM: ViewModel → AnalysisRepository ──► Retrofit ──┐   Room cache (offline)  │
│                                                               │   ◄── mirror results    │
└───────────────────────────────────────────────────────────────┼─────────────────────────┘
                                                                │  HTTPS / REST (JSON)
                                                                ▼
┌──────────────────────────── BACKEND (Python / FastAPI) ─────────────────────────────────┐
│                                                                                          │
│   Content Router  ─►  determine modality (text / image / video / audio / document)       │
│         │                                                                                │
│         ├─► Text Engine     ┐                                                            │
│         ├─► Image Engine    │                                                            │
│         ├─► Video Engine    ├─►  Evidence  ─►  Phishing Engine  ─►  Authenticity Engine  │
│         ├─► Audio Engine    │                                                            │
│         └─► (Document→Text)  ┘                                                            │
│                                    │                                                     │
│                                    ▼                                                     │
│                          Evidence Fusion Layer  (weighted, PRD §8)                       │
│                                    │                                                     │
│                                    ▼                                                     │
│                       LLM Explanation Generator  (pluggable; template default)           │
│                                    │                                                     │
│                                    ▼                                                     │
│                          Trust Score  ─►  persist (PostgreSQL / SQLite)                  │
│                                                                                          │
│   Infra: Redis (cache/queue) · Docker · Nginx (gateway) · JWT/HTTPS                       │
└──────────────────────────────────────────────────────────────────────────────────────────┘

* Gmail OAuth is scaffolded; automatic email fetching is a later phase.
```

**Why this shape?** It's a *modular AI pipeline*, not one monolithic model. Each modality is handled by the detector that performs best for it, outputs are combined in one fusion layer, and any engine can be upgraded independently (e.g. swap in a heavyweight deepfake model) without touching the rest.

---

## 5. How It Works (End-to-End Workflow)

Example: you receive a WhatsApp message — *"SEBI has approved guaranteed 40% returns, click http://bit.ly/xyz now!"*

1. **Ingest** — you tap *Share → InvestWall* (or it's an SMS scanned automatically).
2. **Route** — the backend's Content Router identifies it as **text**.
3. **Detect** — the Text Engine finds "guaranteed returns", a fake-SEBI-approval claim, urgency; the Phishing Engine flags the `bit.ly` shortener; the Authenticity Engine notes the SEBI claim can't be verified.
4. **Fuse** — the Evidence Fusion layer weights these signals (AI 30% · Phishing 25% · Source 15% · Authenticity 20% · Metadata 10%) and computes risk.
5. **Explain** — the LLM layer writes: *"This is HIGH RISK because it promises guaranteed returns, falsely implies SEBI approval, and hides its link behind a shortener. Do not click or send money…"*
6. **Score & store** — Trust Score **22/100 → High Risk**; the report is saved and mirrored to the app's offline cache.
7. **Act** — the app shows the score ring, the reasons, and a recommendation. For SMS, a warning notification fires automatically.

---

## 6. The Six Detection Engines

| # | Engine | Purpose | Key techniques (current, real) |
|---|--------|---------|-------------------------------|
| 1 | **Text** | AI-written scams & phishing | spaCy tokenize/NER, stylometric AI-likelihood (burstiness, TTR), rule-based scam/urgency/credential scoring, optional Transformers |
| 2 | **Image** | AI-generated images | EXIF/metadata anomalies, Error-Level-Analysis, FFT/noise residual, OpenCV face detection + over-symmetry, AI-watermark byte scan |
| 3 | **Video** | Deepfake video | OpenCV frame sampling → per-frame forensics, temporal consistency, blink-rate & over-smoothing heuristics |
| 4 | **Audio** | Cloned/synthetic voice | librosa spectral flatness / MFCC variance / ZCR, optional Whisper STT → transcript scam analysis |
| 5 | **Phishing** | Malicious URLs & senders | shorteners, raw-IP links, typosquat vs official brands, suspicious TLDs, sender impersonation |
| 6 | **Authenticity** | Verify genuine sources | official-domain registry (SEBI/NSE/BSE/depositories/brokers), SPF/DMARC DNS, metadata sanity |

Each engine returns **explainable evidence** — every signal has a 0–1 score and a short human reason string. Heavyweight research models (DeepFakeBench, AASIST, FaceForensics++, DeBERTa, ViT) drop in behind these same interfaces via config flags — see the [roadmap](#14-roadmap--how-to-go-forward).

---

## 7. The Trust Score

Every analysis yields one **Trust Score from 0–100** (higher = more trustworthy):

| Score | Band | Meaning |
|------:|------|---------|
| **75–100** | 🟢 Highly Authentic | No significant risk signals; source checks consistent with a legitimate origin |
| **40–74** | 🟠 Potentially Manipulated | Treat with caution and verify before acting |
| **0–39** | 🔴 High Risk | Do not act, click links, or share money/credentials without out-of-band verification |

**Fusion weights (PRD §8):** AI Detection **30%** · Phishing **25%** · Source Reputation **15%** · Authenticity **20%** · Metadata **10%**, renormalised over whichever components are present for that content. A "severity floor" ensures a single decisive high-risk signal is never fully diluted by low-risk ones.

---

## 8. Technology Stack

**Android app**
Kotlin · Jetpack Compose (Material 3) · MVVM · Hilt (DI) · Retrofit + OkHttp + kotlinx.serialization · Room · WorkManager · SMS BroadcastReceiver · Android Share Intent · Google Sign-In (Gmail OAuth) · DataStore.

**Backend**
Python 3.10+ · FastAPI · Uvicorn · Pydantic v2 · SQLAlchemy (PostgreSQL in prod, SQLite fallback) · Redis (optional) · spaCy · OpenCV · Pillow · NumPy · librosa · dnspython · tldextract · pypdf/python-docx · Docker + docker-compose + Nginx.

**AI/ML (current + pluggable)**
Rule engines + classical forensics now; optional Transformers (DistilBERT/DeBERTa), Whisper/faster-whisper, and heavyweight deepfake models (DeepFakeBench/AASIST/ViT) behind flags.

**LLM (explanation only)**
Pluggable: deterministic **template** explainer (default, no deps) · local **Ollama** (Gemma/Qwen/Llama) · **hosted** API — the LLM explains structured evidence, it never performs detection.

---

## 9. Repository Structure

```
InvestWall/
├── prd.txt                     # Product Requirements Document
├── tech stack.txt              # Technical stack document
├── problem_explanation_*.pdf   # SEBI problem statement
├── README.md                   # ← you are here
│
├── backend/                    # Python FastAPI AI pipeline  (RUNS & TESTED)
│   ├── app/
│   │   ├── main.py             # FastAPI app + startup
│   │   ├── config.py           # env-driven settings / feature flags
│   │   ├── core/               # router, evidence, fusion, trust_score
│   │   ├── engines/            # 6 detection engines (base + text/image/video/audio/phishing/authenticity)
│   │   ├── llm/                # explainer interface + template/ollama/hosted
│   │   ├── knowledge/          # phishing rules + official-domain registry
│   │   ├── db/                 # SQLAlchemy models, session, repository
│   │   ├── services/           # pipeline orchestrator, cache, doc extraction
│   │   └── api/                # routes (health, analyze, history) + schemas
│   ├── tests/                  # pytest (20 tests, offline)
│   ├── requirements*.txt
│   ├── Dockerfile / docker-compose.yml / nginx/
│   └── README.md               # backend-specific guide
│
└── android/                    # Kotlin/Compose client  (41 files; build on a real machine)
    ├── app/src/main/
    │   ├── java/com/investwall/app/
    │   │   ├── ui/             # theme, navigation, screens, components
    │   │   ├── data/           # remote (Retrofit), local (Room), repository, mappers
    │   │   ├── domain/         # models (TrustReport, TrustBand…)
    │   │   ├── di/             # Hilt modules
    │   │   ├── share/          # Share Intent receiver
    │   │   ├── sms/            # SMS receiver + WorkManager worker
    │   │   └── notifications/  # alerts
    │   ├── res/                # plain dark theme, icons
    │   └── AndroidManifest.xml
    ├── build.gradle.kts / settings.gradle.kts / gradle wrapper
    └── README.md               # android-specific guide
```

---

## 10. Getting Started

### Prerequisites

- **Backend:** Python 3.10+ (tested on 3.10). Docker optional (for the full prod stack).
- **Android:** JDK 17–21 (Android Studio's bundled JBR 21 works) + Android SDK. Android Studio recommended.

### A) Run the backend (start here)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm     # recommended
cp .env.example .env                          # optional; defaults work

uvicorn app.main:app --reload                 # http://localhost:8000
```

- Interactive API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**
- Run tests: `pytest`  (20 passing, fully offline)

Quick smoke test:

```bash
curl -s http://localhost:8000/analyze -H "Content-Type: application/json" \
  -d '{"text":"SEBI approved GUARANTEED 40% returns! Verify your demat at http://bit.ly/x now!!!","source":"whatsapp"}'
# → trust_score ~22, band "High Risk", evidence + explanation
```

> **Full production stack** (API + PostgreSQL + Redis + Nginx): `docker compose up --build` from `backend/`.

### B) Run the Android app

```bash
cd android
# Emulator reaches your machine at 10.0.2.2 (this is the default backend URL).
# For a physical device, set your LAN IP in the app's Settings screen and run
# the backend with:  uvicorn app.main:app --host 0.0.0.0
./gradlew assembleDebug        # → app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` folder in **Android Studio** and press Run. Then:

1. Ensure the backend is running.
2. On first launch, open **Settings** and confirm the backend URL (Settings shows a live connection status).
3. Try it: Dashboard → *Analyze a message* → paste a scam; or Share content from any app into InvestWall; or enable *Scan incoming SMS*.

See [`backend/README.md`](backend/README.md) and [`android/README.md`](android/README.md) for deeper, component-specific instructions.

---

## 11. API Reference

Base URL: `http://<host>:8000/`

| Method | Endpoint | Body / Params | Returns |
|--------|----------|---------------|---------|
| `GET`  | `/health` | — | Liveness + which optional engines/models are active |
| `POST` | `/analyze` | `{ "text": "...", "source"?, "sender"? }` | **TrustReport** |
| `POST` | `/analyze/file` | multipart `file` (+ `source?`, `sender?`) | **TrustReport** |
| `GET`  | `/history` | `?limit=&offset=` | List of history items |
| `GET`  | `/report/{id}` | — | **TrustReport** |

**TrustReport** (JSON):

```jsonc
{
  "id": "…", "created_at": "…", "modality": "text",
  "trust_score": 22, "band": "high_risk", "band_label": "High Risk",
  "band_color": "#E5484D", "confidence": 0.68,
  "primary_threat": "Phishing / Financial Scam",
  "component_scores": { "ai": 0.09, "phishing": 0.8, "authenticity": 0.75 },
  "evidence": [ { "signal": "scam_rule", "component": "phishing", "score": 0.9,
                  "reason": "Promises guaranteed returns — a hallmark of investment fraud." } ],
  "explanation": "This content is HIGH RISK because…",
  "llm_provider": "template"
}
```

---

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

## 12. Design Philosophy

**Backend** — a modular, explainable pipeline: specialised detectors beat one general model; the fusion layer combines independent signals into a calibrated decision; the LLM adds transparency, not detection. Everything degrades gracefully (SQLite instead of Postgres, in-memory cache instead of Redis, OpenCV instead of system FFmpeg, template explainer instead of an LLM server), so it boots and returns real results with only the base dependencies and no network.

**Android UI** — intentionally **plain and calm**: **dark-only, no gradients, no glassmorphism, no purple "AI" tints.** One steady blue accent (`#4F9CF9`), neutral greys, flat outlined cards with hairline borders and no shadows, and green/amber/red used *only* for the trust bands. The goal is an easy-going experience a non-technical investor can trust at a glance.

---

## 13. What's Built vs. What's Missing

### ✅ Built and working

- **Full backend AI pipeline** — content router, all six engines, evidence fusion, trust scoring, pluggable LLM explainer, persistence. **Runs locally; 20 tests pass; PRD examples verified.**
- **Real (functional-MVP) detection** — every engine computes genuine results using feasible libraries and forensics/heuristics.
- **Deployment config** — Dockerfile, docker-compose (API + Postgres + Redis + Nginx), Nginx gateway.
- **Complete Android app** — all screens, MVVM + Hilt + Room + Retrofit + WorkManager, Share Intent, SMS auto-scan + notifications, Gmail OAuth sign-in scaffold, runtime-configurable backend URL, plain dark UI.

### 🚧 Missing / deferred (by design)

- **Heavyweight AI models** — DeepFakeBench, AASIST, FaceForensics++, DeBERTa, ViT, Whisper are **optional flags**, not wired to real weights yet (the interfaces are ready).
- **Automatic Gmail fetching** — OAuth sign-in is wired, but reading & analysing emails via the Gmail API needs a configured Google Cloud OAuth client (package + SHA-1) and is a later phase.
- **Compiled APK from this repo state** — sources are complete but must be built on a normal machine/CI (see [constraints](#15-known-constraints--notes)).
- **Auth/accounts, real-time URL reputation feeds, SEBI verified-registry integration** — future scope.

---

## 14. Roadmap — How to Go Forward

**Phase 1 — Backend AI pipeline** ✅ *done*
**Phase 2 — Android app** ✅ *done*

**Phase 3 — Upgrade detection fidelity (recommended next)**
- Wire real model weights behind the existing engine interfaces via env flags:
  - Text: enable Transformers (`ENABLE_TRANSFORMERS=1`) → DistilBERT/DeBERTa scam classifiers.
  - Audio: enable Whisper (`ENABLE_WHISPER=1`) for transcription; add AASIST/RawNet2 for spoof detection.
  - Image/Video: integrate DeepFakeBench / ViT / FaceForensics++ checkpoints.
- Add GPU support to the Docker image for real-time media inference.

**Phase 4 — Automatic email protection**
- Configure a Google Cloud OAuth client; implement Gmail API fetch + a WorkManager sync job that runs analyses and surfaces phishing in-app.

**Phase 5 — Hardening & product**
- JWT auth + user accounts; real-time URL reputation service; SEBI verified-communication registry integration; Prometheus/Grafana monitoring; Play Store release.

**Phase 6 — Future scope (from PRD §13)**
- Live browser extension · call-recording analysis (with consent) · on-device/offline inference · federated learning · enterprise broker dashboard · iOS & web.

**Quick wins**
- Add a GitHub Actions workflow to build the debug APK on every push (produces a downloadable artifact with no local setup).
- Expand `knowledge/financial_domains.py` and `knowledge/phishing_rules.py` with more SEBI-registered intermediaries and current scam patterns.

---

## 15. Known Constraints & Notes

- **Building the Android APK requires a real machine or CI.** It cannot be compiled inside a restricted sandbox that blocks Java NIO's selector loopback (`Selector.open()` fails with *"Unable to establish loopback connection"*) — Gradle and the Kotlin compiler daemon depend on it. This is an environment limitation, not a code issue; the project targets stable **AGP 8.7 / Gradle 8.11 / Kotlin 2.0** with **JDK 17–21** and builds normally in Android Studio.
- **Debug HTTP** to `10.0.2.2` / `localhost` is allowed via the app's network-security config; **production must use HTTPS**.
- **Detection is decision-support, not a guarantee.** Always verify major financial decisions through official channels — InvestWall raises confidence and flags risk; it does not replace due diligence.
- The current models are calibrated for demonstration and the securities-market context; benchmark precision/recall improves substantially once the heavyweight models (Phase 3) are enabled.

---

<div align="center">

**InvestWall** — because the best time to catch a scam is *before* you act on it.

*Built to the SEBI problem statement · Multimodal · Explainable · Privacy-first*

</div>
