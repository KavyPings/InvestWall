# InvestWall — Start Guide

Exact steps to run the whole app (Windows / PowerShell). Two parts: the **backend**
(Python API + AI models) and the **Android app**. Start the backend first.

---

## 1) Backend (run this first)

```powershell
# Go to the backend folder (NOT android/ — that's where the earlier error came from)
cd "C:\Users\Kavy Khilrani\Desktop\Projects\InvestWall\backend"

# First time only: create + activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# First time only: install everything (single file; ~2 GB — includes PyTorch + models)
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env          # optional; defaults work

# Start the API (every time)
uvicorn app.main:app --host 0.0.0.0 --reload
```

- After activating once, later runs are just:
  `.venv\Scripts\activate` then the `uvicorn ...` line.
- Verify it's up: open <http://localhost:8000/health> — you should see JSON with
  `"status":"ok"` and the model flags.
- **First image/text/audio analysis is slow** while a model downloads/loads, then
  it's cached and fast. `/health` shows `image_model_loaded` / `transformer_loaded`
  flipping to `true` after the first use.

> Smaller/faster torch (optional): before `pip install -r requirements.txt`, run
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`.

> `backend/ml/` is a **separate** offline pipeline for *retraining* the text model.
> You do **not** need it to run the app — ignore `ml/requirements.txt`.

---

## 2) Android app

Make sure an emulator is running (or a phone with USB debugging is plugged in),
then:

```powershell
cd "C:\Users\Kavy Khilrani\Desktop\Projects\InvestWall\android"
.\gradlew installDebug
& "C:\Android\sdk\platform-tools\adb.exe" shell am start -n com.investwall.app.debug/com.investwall.app.MainActivity
```

Or open the `android` folder in **Android Studio** and press **Run ▶**.

### Point the app at the backend
- **Emulator:** already works — the default URL `http://10.0.2.2:8000/` reaches your PC.
- **Physical phone:** open the app → **Settings** → set Base URL to your PC's LAN IP
  (e.g. `http://192.168.1.5:8000/`, find it with `ipconfig`). Phone + PC on same Wi-Fi,
  and run the backend with `--host 0.0.0.0` (already in the command above).

Settings shows a green **Connected** status when it can reach the backend.

---

## 3) Quick smoke test

- **Text (on-device, instant):** Dashboard → *Analyze a message* → paste
  `"SEBI approved guaranteed 40% returns, click http://bit.ly/x"` → High Risk.
- **Deep AI check:** open that report → **Run deep AI check** (uses the backend).
- **Image/deepfake:** Analyze → **Choose a file** → pick a photo. (Drag an image
  onto the emulator window or `adb push photo.jpg /sdcard/Download/` to have one.)
- **Share:** from any app (WhatsApp, gallery) → Share → **Analyze with InvestWall**.

---

## Common issues

| Symptom | Fix |
|---|---|
| `Could not open requirements file` | You're in the wrong folder — `cd backend` first. |
| `./gradlew` fails with `25.0.2` | JDK mismatch; already fixed via `org.gradle.java.home` in `android/gradle.properties`. |
| App says can't reach backend | Backend not running, or wrong URL in Settings (emulator = `10.0.2.2`). |
| First analysis hangs a while | Model is downloading/loading on first use — subsequent calls are fast. |
