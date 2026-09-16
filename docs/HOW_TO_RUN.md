# How to Run the NeuroSense AI App

Windows PowerShell guide for the desktop prototype.

---

## 1. One-time setup

```powershell
cd C:\neurosense-dev
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your Anthropic key (needed only for Claude):

```env
CLAUDE_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-6
```

**Always use the project venv.** System `python` often fails with `Python was not found` or missing packages.

```powershell
.\venv\Scripts\Activate.ps1
```

Or call venv Python directly (no activate):

```powershell
.\venv\Scripts\python.exe <script> ...
```

---

## 2. The three scripts (what each does)

| # | Script | Required? | What it does |
|---|--------|-----------|--------------|
| 1 | `audio_analyzer.py` | **Yes** | Acoustic features + emotional state + chart + saves history |
| 2 | `claude_demo.py` | For full AI narrative | Claude assessment, optional email alert, saves history |
| 3 | `session_history.py` | Optional | Views saved sessions / trends (does not re-analyze) |

Optional: `simple_recorder.py` — record a new mic clip first.

---

## 3. Typical run (existing audio file)

### Step A — Acoustic + emotional analysis

```powershell
cd C:\neurosense-dev
.\venv\Scripts\python.exe audio_analyzer.py recordings\008-Patient.wav --subject 0008 --patient-only
```

`008-Patient.wav` is patient-only (interviewer off-mic). `--patient-only` collapses silences longer than 2s so pause/rate/sadness scores reflect the speaker’s turns, not turn-taking gaps. Omit the flag for clips where long pauses are actually the speaker.

You get:

- Pitch, rate, intensity, voice quality, pauses, prosody, articulation  
- Emotional state: stress / sadness / anger / neutral (0–5, green/yellow/red)  
- Volatility + confidence  
- Chart under `recordings\analysis_*.png`  
- Row in `data\neurosense_history.db`

### Step B — Full Claude assessment

```powershell
.\venv\Scripts\python.exe claude_demo.py --file recordings\008-Patient.wav --subject 0008 --patient-only
```

Needs a **valid** `CLAUDE_API_KEY` in `.env`. A `401 authentication_error` means the key is invalid/revoked — replace it at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

### Step C — View history (optional)

```powershell
.\venv\Scripts\python.exe session_history.py --subject 0008
.\venv\Scripts\python.exe session_history.py --subjects
.\venv\Scripts\python.exe session_history.py --tags
```

---

## 4. Other useful commands

**Newest file in `recordings\`:**

```powershell
.\venv\Scripts\python.exe audio_analyzer.py
```

**Specific path + context tag:**

```powershell
.\venv\Scripts\python.exe audio_analyzer.py "D:\path\to\file.mp3" --subject 0008 --tag "early study"
.\venv\Scripts\python.exe claude_demo.py --file "D:\path\to\file.mp3" --subject 0008 --tag "early study"
```

**Record a short test clip:**

```powershell
.\venv\Scripts\python.exe simple_recorder.py --subject 0008
```

**Feature extractor smoke test only:**

```powershell
.\venv\Scripts\python.exe enhanced_features.py
```

---

## 5. Where outputs live

| Path | Contents |
|------|----------|
| `recordings\` | Audio + `analysis_*.png` charts |
| `data\neurosense_history.db` | Session scores / history (SQLite) |
| `.env` | API keys (never commit) |
| `alert_emails.json` | Optional alert recipients |

---

## 6. Common problems

| Symptom | Fix |
|---------|-----|
| `Python was not found` | Use `.\venv\Scripts\python.exe` or activate the venv first |
| `No module named 'matplotlib'` | Same — you’re on system Python, not the venv |
| Chaining `Activate.ps1` and `python` on one line | Run them as **two separate** commands |
| Claude `401` / API key invalid | Key is loaded from `.env` but Anthropic rejects it — create a new key |
| Long pauses / high pause ratio / “sad” on an interview clip | Interviewer was likely off-mic — re-run with `--patient-only` |
| Can’t load MP3/M4A | Install ffmpeg on PATH; ensure `librosa` is in the venv |

---

## 7. Quick copy-paste (participant 0008 example)

```powershell
cd C:\neurosense-dev
.\venv\Scripts\python.exe audio_analyzer.py recordings\008-Patient.wav --subject 0008 --patient-only
.\venv\Scripts\python.exe claude_demo.py --file recordings\008-Patient.wav --subject 0008 --patient-only
.\venv\Scripts\python.exe session_history.py --subject 0008
```
