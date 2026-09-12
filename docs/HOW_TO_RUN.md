# How to Run NeuroSense AI

Quick start for the desktop prototype on Windows (PowerShell).

## 1. Always use the project venv

System Python will fail with errors like `No module named 'matplotlib'`.

```powershell
cd c:\neurosense-dev
.\venv\Scripts\Activate.ps1
```

Your prompt should show `(venv)`. Or call the venv Python directly (no activate):

```powershell
.\venv\Scripts\python.exe audio_analyzer.py
```

First-time setup (if venv is missing):

```powershell
cd c:\neurosense-dev
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env` with `CLAUDE_API_KEY` (and SMTP settings if you want email alerts) before running the Claude pipeline.

## 2. Record a clip

```powershell
python simple_recorder.py --subject person1
```

Saves under `recordings\person1\recording_NNN.wav`.

## 3. Analyze (metrics + chart + history)

Extracts the researcher acoustic set (pitch, rate, intensity, voice quality, pauses, prosody, articulation) plus composite stress/behavioral scores.

Newest file under `recordings\`:

```powershell
python audio_analyzer.py
```

By subject, specific file, or with a context tag:

```powershell
python audio_analyzer.py --subject person1
python audio_analyzer.py "D:\Neurosense AI\audio\AO 4-14-26 2.41PM - 008.mp3" --subject ao
python audio_analyzer.py --subject person1 --tag "morning check-in"
```

Quick smoke-test of the extractor only:

```powershell
python enhanced_features.py
```

## 4. Full Claude pipeline (AI + optional alert)

```powershell
python claude_demo.py --subject person1 --file recordings\person1\recording_001.wav
python claude_demo.py --subject person1 --file recordings\person1\recording_001.wav --tag "after work"
```

## 5. View history / trends

```powershell
python session_history.py
python session_history.py --subjects
python session_history.py --subject person1
python session_history.py --tags
```

## Useful paths

| Path | What |
|------|------|
| `recordings\` | Local clips + analysis PNGs |
| `D:\Neurosense AI\audio\` | Batch telephony MP3s (AO / MD / DW) |
| `data\neurosense_history.db` | Session history (SQLite) |
| `.env` | API keys / SMTP |
| `alert_emails.json` | Alert recipients |

## 6. Running remotely (AWS)

Today the app is a **local CLI**. For Amy / production, run NeuroSense as a secured **analyze API** on AWS. Amy’s poller sends a job; NAI pulls audio over HTTPS and returns scores.

### Target flow

```text
Amy DB poller (new files row)
  → POST /v1/analyze  { amy_call_id, signed audio_url, metadata }
  → NAI downloads audio (HTTPS, short-lived URL)
  → enhanced_features + Claude
  → webhook / response → Amy UI (leave "Processing..." until done)
```

Do **not** use FTP. Prefer signed `files.file_url` pull.

### Recommended AWS shape

| Concern | Pilot (fast) | Production |
|---------|----------------|------------|
| Compute | Small **EC2** or **ECS Fargate** running FastAPI | **API Gateway** + **SQS** + **Fargate** worker |
| Long calls (10+ min) | Fargate / EC2 | Same — avoid short Lambda-only for heavy jobs |
| Secrets | `.env` on box → move to **Secrets Manager** | `CLAUDE_API_KEY`, webhook HMAC |
| Results | Local SQLite OK for demo | **DynamoDB** or **RDS**, keyed by Amy `files.id` |
| Audio retention | Delete after analyze | Metrics-only by default |

### What to wrap

Reuse as-is inside the container/service:

- `enhanced_features.py` — scores
- `claude_analyzer.py` — narrative / status
- `session_history.py` — optional NAI-side history
- `alert_sender.py` — optional care-team email

New work: thin **FastAPI** `POST /v1/analyze`, Docker image, API key auth, deploy to AWS.

### Minimal pilot checklist

1. Dockerize the Python venv + ffmpeg (for MP3/M4A)
2. Add `POST /v1/analyze` that accepts `audio_url` + `amy_call_id`
3. Deploy to one Fargate service or EC2 behind HTTPS
4. Store `CLAUDE_API_KEY` in Secrets Manager
5. Give Amy an API key; point their poller at the URL
6. Confirm Connect Converse leaves Total Score on `Processing...` until NAI returns

### Local vs AWS

| | Local (`HOW_TO_RUN` §1–5) | AWS |
|--|---------------------------|-----|
| Who runs it | You, on this PC | Always-on service |
| Who calls it | You in PowerShell | Amy poller / partners |
| Auth | Your `.env` | API key + TLS |
| Best for | Demos, batch files | Product integration |

## Common failure

| Symptom | Fix |
|---------|-----|
| `No module named 'matplotlib'` (or similar) | Activate venv or use `.\venv\Scripts\python.exe` |
| Claude API errors | Set `CLAUDE_API_KEY` in `.env` |
| Can't load MP3/M4A | Install ffmpeg on PATH + `pip install librosa` in the venv |
| Amy can't reach NAI | Confirm HTTPS URL, API key, and security group / API Gateway auth |
| Job stuck on `Processing...` | Check NAI logs + webhook/callback to Amy; verify signed URL not expired |
