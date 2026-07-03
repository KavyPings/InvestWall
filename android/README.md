# InvestWall — Android App

Native Android client for the InvestWall backend. It ingests content (typed
messages, shared files, incoming SMS), sends it to the FastAPI analysis API, and
renders an explainable **Trust Score** with evidence — all in a plain, dark,
flat UI.

## Stack (PRD §10 / tech-stack §3)

Kotlin · Jetpack Compose (Material 3) · MVVM · Hilt (DI) · Retrofit + OkHttp +
kotlinx.serialization · Room (offline cache) · WorkManager · SMS BroadcastReceiver ·
Android Share Intent · Google Sign-In (Gmail OAuth scaffold) · DataStore.

## Design

Deliberately plain: **dark-only**, **no gradients, no glassmorphism, no purple**.
One calm blue accent (`#4F9CF9`), neutral greys, and three semantic Trust colours
— green / amber / red — matching the backend bands. Flat outlined cards, hairline
borders, no drop shadows. See `ui/theme/Color.kt`.

## Architecture

```
UI (Compose screens)
  → ViewModel (StateFlow, MVVM)
    → AnalysisRepository  ── Retrofit ──► FastAPI backend
                          └─ Room cache (offline history, revisit reports)
```

- **Screens**: Dashboard, Analyze (typed message), Trust Report (score ring +
  breakdown + evidence + explanation), History, Settings.
- **Ingestion**:
  - *Share Intent* — `ShareReceiverActivity` accepts text/image/video/audio/PDF
    shared from WhatsApp, browser, gallery, files, etc. (PRD §5).
  - *SMS* — `SmsReceiver` → `SmsAnalysisWorker` (WorkManager) analyses incoming
    texts in the background and raises a notification when risky (opt-in).
  - *Email* — `GmailConnector` wires the Google OAuth sign-in + Gmail read-only
    scope (fetch/analyse of messages is a later phase; see the class doc).
- **Networking**: `BaseUrlProvider` rewrites the request host at runtime so the
  backend URL is configurable from Settings without a rebuild.

## Build & run

Requires **JDK 17–21** (the bundled Android Studio JBR 21 works) and the Android
SDK. `local.properties` already points at `C:\Android\sdk`; edit if yours differs.

```bash
cd android
# Point the app at your backend (emulator → host is 10.0.2.2):
#   optionally add BACKEND_URL=http://10.0.2.2:8000/ to local.properties
./gradlew assembleDebug          # build the debug APK
# → app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` folder in **Android Studio** and Run.

### Connecting to the backend

1. Start the backend (`cd ../backend && uvicorn app.main:app`).
2. **Emulator**: default URL `http://10.0.2.2:8000/` reaches your machine.
   **Physical device**: set your machine's LAN IP in Settings → Backend server
   (e.g. `http://192.168.1.5:8000/`), and run the backend with
   `uvicorn app.main:app --host 0.0.0.0`.
3. Settings shows a live connection status.

Cleartext HTTP to `10.0.2.2` / `localhost` is permitted in debug via
`res/xml/network_security_config.xml`. Production should use HTTPS.

## Try it

- **Typed**: Dashboard → *Analyze a message* → paste a scam → see the Trust Report.
- **Shared**: from any app, Share → **InvestWall** → get a compact result.
- **SMS**: Settings → enable *Scan incoming SMS* (grants RECEIVE_SMS) → risky
  texts trigger a warning notification.

## Notes / later phases

- **Google OAuth**: sign-in is wired but needs an OAuth client configured in
  Google Cloud (this app's package + SHA-1) to succeed on a device; actual Gmail
  fetching/analysis is deferred.
- Heavyweight detection models are added on the backend side, behind its existing
  engine interfaces — no app changes required.

> Build note: this project must be built with Gradle on a normal machine or CI.
> It cannot be compiled inside the assistant's sandbox because that environment
> blocks the Java NIO selector loopback (`Selector.open()` fails), which Gradle
> and the Kotlin compiler daemon require. The sources are complete and target
> stable AGP 8.7 / Gradle 8.11 / Kotlin 2.0 with JDK 21.
```
