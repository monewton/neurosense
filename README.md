# NeuroSense AI

Desktop prototype for acoustic behavioral analysis: load a voice clip, extract pitch/rate/quality/pause features, infer emotional state, and optionally ask Claude for a clinical-style narrative.

The run guide and product write-up were already in the repo (`docs/HOW_TO_RUN.md`, `NEUROSENSE_AI_SUMMARY.md`). GitHub only auto-displays a root **`README.md`**, which is this file.

## Quick start (Windows)

```powershell
cd C:\neurosense-dev
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Put your Anthropic key in `.env` if you want Claude. Then:

```powershell
.\venv\Scripts\python.exe audio_analyzer.py recordings\008-Patient.wav --subject 0008 --patient-only
.\venv\Scripts\python.exe claude_demo.py --file recordings\008-Patient.wav --subject 0008 --patient-only
.\venv\Scripts\python.exe session_history.py --subject 0008
```

Use `--patient-only` when the interviewer is off-mic (long silences are turn-taking, not patient pauses). Full commands and troubleshooting: [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md).

## What it does

1. **`audio_analyzer.py`** — acoustic features, emotional state (stress / sadness / anger / neutral), chart, session history
2. **`claude_demo.py`** — same pipeline plus Claude assessment (optional email alert)
3. **`session_history.py`** — view saved sessions and trends

## Docs

| File | Contents |
|------|----------|
| [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md) | Setup, commands, common problems |
| [docs/HOW_IT_WORKS_DEV.md](docs/HOW_IT_WORKS_DEV.md) | Architecture and feature contract |
| [docs/HOW_IT_WORKS_INVESTORS.md](docs/HOW_IT_WORKS_INVESTORS.md) | Product / strategy overview |
| [NEUROSENSE_AI_SUMMARY.md](NEUROSENSE_AI_SUMMARY.md) | Longer application summary |

Local recordings and the SQLite history DB stay on disk (`recordings/`, `data/`) and are gitignored.
