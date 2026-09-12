# NeuroSense AI — Porting to a Wearable

This document maps how to bring NeuroSense AI’s pipeline (capture → features → Claude → alerts) onto a wearable device.

---

## 1. Current Pipeline (Reference)

| Step | Where it runs | Key components |
|------|----------------|----------------|
| **Capture** | Desktop | `sounddevice`, `soundfile` — 44.1 kHz mono, configurable duration |
| **Feature extraction** | Desktop | `numpy` — RMS, peak, FFT (80–1000 Hz), frame energy, speech ratio, vocal stability, behavioral score |
| **AI interpretation** | Cloud | `claude_analyzer.py` — HTTP to Anthropic API with feature dict |
| **Alerts** | Desktop | `alert_sender.py` — SMTP to addresses in `alert_emails.json` when status is "Needs Attention" |

Data flow: **Audio → feature dict (small) → Claude API → status + raw analysis → optional email.**

---

## 2. Wearable Constraints

- **Battery** — Continuous mic and compute drain quickly; prefer burst capture and/or offload.
- **Compute** — Limited CPU/RAM; heavy numpy/FFT may need lighter impl or move to phone/cloud.
- **Memory** — Little room for large buffers or full WAVs; streaming or short chunks.
- **Mic** — Often lower quality, more noise, different placement (wrist vs body); may need different gain/normalization or preprocessing.
- **Connectivity** — Usually BLE to phone; cellular wearables are rare. Assume “wearable ↔ phone ↔ cloud.”
- **Privacy** — Prefer on-device or on-phone feature extraction so raw audio never leaves the user’s control unless required.

---

## 3. Possible Architectures

### Option A: Wearable captures → phone does rest

- **Wearable:** Record short segments (e.g. 5–15 s) or stream chunks over BLE to phone. Minimal logic (record, maybe VAD to start/stop).
- **Phone:** Buffers audio, runs feature extraction (port of current logic or lighter version), calls Claude API, handles alerts (e.g. push + backend sends email).
- **Pros:** Reuses most of your Python feature + Claude + alert logic on phone (e.g. Kivy, BeeWare, or a small backend on the phone). Wearable stays simple and power-efficient.
- **Cons:** Phone must be present and running the app; latency depends on phone.

### Option B: Wearable captures → cloud does everything

- **Wearable:** Record, then send compressed audio (or chunks) to phone, which forwards to your backend (or wearable has Wi‑Fi/cellular and sends directly).
- **Backend:** Same as today — feature extraction + Claude + alerts. Backend can be your current Python stack.
- **Pros:** Easiest to keep current code; wearable and phone stay thin.
- **Cons:** Raw audio over the network (privacy, bandwidth, cost); wearable or phone needs good connectivity.

### Option C: On-wearable feature extraction

- **Wearable:** Record + run a lightweight feature pipeline (RMS, energy, simple spectral band energy, speech ratio). Send only the **feature vector** to phone or cloud.
- **Phone/cloud:** Forward features to Claude (and optionally trigger alerts).
- **Pros:** No raw audio leaves the device; small payloads; can work with intermittent connectivity.
- **Cons:** Need a second implementation of feature extraction (C/C++ or Kotlin/Swift for Wear OS/watchOS, or C for MCU).

---

## 4. Platform Choices (Wearable side)

| Platform | Language / runtime | Audio | Suggested role |
|----------|--------------------|--------|----------------|
| **Wear OS** | Kotlin/Java | Android AudioRecord, etc. | Capture + optional on-device features; BLE to phone or HTTP to backend |
| **watchOS** | Swift | AVAudioEngine, etc. | Same idea; WatchConnectivity to iPhone app |
| **ESP32 / custom** | C/C++, Arduino | I2S mic, PDM | Capture + stream over BLE; feature extraction on phone or server |
| **Garmin / Fitbit** | vendor SDKs | Limited or no raw mic | Only if you add a “companion phone app” that does capture on the phone and uses the wearable for UI/notifications |

Choose based on whether you need **mic on the wrist** (Wear OS / watchOS) or are okay with **body-worn mic + small MCU** (ESP32, etc.).

---

## 5. What to Reuse vs Reimplement

- **Reuse as-is (backend or phone):**
  - Claude API integration (`claude_analyzer.py`): same prompts, same feature dict format.
  - Alert logic: same “Needs Attention” rule and SMTP (or replace with push + server-side email).
  - Feature schema: keep `rms_energy`, `peak_amplitude`, `dominant_frequency`, `speech_ratio`, `vocal_stability`, `pitch_variation`, `behavioral_score` so the rest of the pipeline stays unchanged.

- **Port / reimplement:**
  - **Audio capture:** Use platform APIs (Wear OS AudioRecord, watchOS AVAudioEngine, ESP32 I2S/PDM). Prefer 16 kHz or 44.1 kHz mono; if 16 kHz, document it so feature math (e.g. vocal range 80–1000 Hz) is still valid.
  - **Feature extraction:** Either port the math to the wearable (C/Kotlin/Swift) or run the same logic on the phone/backend. For a first port, running on phone or backend is faster; optimize to on-device later if needed.
  - **Alerts on wearable:** Add push/notification from phone or backend; keep email as a separate channel (e.g. backend still uses `alert_sender` when status is "Needs Attention").

---

## 6. Suggested Phased Plan

1. **Phase 1 — Phone as “wearable proxy”**  
   Run the existing Python pipeline on a **phone** (e.g. Termux + Python, or a small Flask/FastAPI app on a home server). Use the phone’s mic to record and send to the same feature + Claude + alert flow. Validates “mobile” form factor and connectivity without wearable SDK work.

2. **Phase 2 — Wearable as capture-only**  
   Build a minimal wearable app (Wear OS or watchOS) that records short segments and sends audio to the phone (or backend). Phone/backend runs current feature + Claude + alert code. No need to port numpy/FFT to the device yet.

3. **Phase 3 — Optional on-device features**  
   If you need lower latency or privacy, port a minimal feature extractor (RMS, frame energy, simple FFT or band energies) to the wearable and send only the feature dict; keep Claude and alerts on phone/cloud.

4. **Phase 4 — Alerts on the wrist**  
   When status is "Needs Attention", trigger a push to the wearable (and keep email via your existing `alert_sender`).

---

## 7. File / Module Mapping

| Current | Wearable / companion role |
|--------|----------------------------|
| `claude_demo.py` (record + extract + Claude) | Split: capture in wearable/phone app; feature extraction in phone or backend; Claude + summary in backend or phone. |
| `claude_analyzer.py` | Use unchanged from backend or phone (same HTTP + prompt + parsing). |
| `alert_sender.py` | Run on backend or phone; add push/notification to wearable. |
| `alert_emails.json` | Unchanged; backend/phone still reads it for email. |
| Feature dict format | Keep identical so Claude and status logic don’t change. |

---

## 8. Risks and Mitigations

- **Mic quality on wrist:** Noisy; consider noise gate, level normalization, and possibly retraining or relaxing “concerning” thresholds in Claude prompts.
- **Sample rate / format:** If wearable uses 16 kHz, ensure FFT and frequency bounds (e.g. 80–1000 Hz) are still correct in the feature code.
- **Battery:** Use short, scheduled recordings (e.g. 10 s every N minutes) and avoid continuous streaming in v1.
- **Privacy / compliance:** Prefer sending only feature vectors (Option C) or clearly document where audio is stored and who can access it (Option B).
