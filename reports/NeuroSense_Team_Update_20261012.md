# NeuroSense AI — Product update for the team

**Date:** October 12, 2026  
**On `main`:** commit `515deee`  
**Audience:** engineering, clinical, and dashboard partners

This note covers what just shipped and how to use it. You can forward it as-is.

---

## In one sentence

Sessions now tell you **whether this visit looks different from this same person**, and **whether the recording itself is trustworthy** — in the same compact JSON the dashboard already consumes.

Scores without those two layers are easy to misread. A “Fair” behavioral score on a clipped 8 kHz phone clip is not the same finding as a Fair score on a clean later visit. A 10-point stress jump vs. this person’s own history is more useful than comparing them to a population average.

---

## 1. Person vs self (`vs_self`)

Each analysis now compares the current visit to **this subject’s prior stored sessions** (all of them, not a 7-day window).

| Status | Meaning |
|--------|---------|
| `no_subject` | We could not read a subject id from `--subject` or the filename |
| `no_baseline` | First stored session for that person — nothing to compare yet |
| `compared` | Deltas vs. that person’s average so far |

Compared metrics:

- **Behavioral score** (0–100)
- **Stress level** (0–100)
- **Speech ratio** (how much of the scored audio is speech)

Each metric reports `current`, `average`, and `delta`. Positive behavioral `delta` means this visit scored higher than their own mean. Positive stress `delta` means this visit is more stressed than their own mean.

This is **not** a population norm and **not** a diagnosis. It answers: *Is this person sounding different from how they usually sound in our files?*

**Talk-track:** “We stopped comparing people to a generic average. Visit two is compared to visit one for the same ID. That’s how you see recovery, strain, or a one-off bad recording instead of treating every 55 the same.”

---

## 2. Quality / trust card (`quality`)

A score can look odd because **capture was odd**. The JSON now includes a quality block so the dashboard can badge a session instead of treating every number as clinical.

Flags we raise today:

| Flag | When it fires |
|------|----------------|
| `telephony_sample_rate` | Sample rate ≤ 8 kHz (typical phone / interview recorders) |
| `possible_clipping` | Peak amplitude ≥ 0.99 |
| `very_short_clip` | Original duration under 5 seconds |
| `patient_only_gaps_collapsed` | `--patient-only` removed long off-mic interviewer gaps |
| `high_offmic_silence` | Those gaps were ≥ 35% of the original file |

The card also reports original duration, scoring duration (after gap collapse), peak amplitude, speech ratio, and how many seconds were removed.

**Talk-track:** “If stress looks high, check the yellow flags first. Phone audio, clipping, and a huge off-mic gap are capture issues — not automatically a clinical change.”

---

## 3. File naming (required for vs-self)

Person-vs-self only works if **every visit for one person shares the same 4-digit subject id**.

Preferred pattern (quote the path if it has spaces):

```text
<SITE> <M-D-YY> <H.MM><AM|PM> - <SUBJECT>.mp3
```

Examples:

```text
AO 4-14-26 2.41PM - 0008.mp3
DW 7-30-26 1.06PM - 0008.mp3
MD 4-29-26 2.55PM - 0008.mp3
```

| Piece | Stored as |
|--------|-----------|
| `AO` / `DW` / `MD` | `source.site` |
| `4-14-26` | `source.interview_date` (ISO: `2026-04-14`) |
| `0008` | `source.subject_id` — always 4 digits (`008` → `0008`) |

Also accepted: `0008-Patient.wav`. Passing `--subject 0008` always wins.

**Left / right:** Keep `-left` / `-right` in your own folder names if you want. They are organizer labels only. They are **not** a product field and are **not** written into the JSON.

If two files for the same person use different ids (`8` vs `008` vs `0008`), they will not be compared. Use **four digits** everywhere.

---

## 4. Dashboard JSON additions

Output is still `recordings/analysis_<stem>.json`, schema `neurosense.session_results.v1`.

New / completed fields in this drop:

- `quality` — trust flags above
- `vs_self` — person-vs-prior comparison
- `source.site` and `source.interview_date` when the filename parses
- `markers.articulation_clarity`
- `markers.slur_index`
- `markers.over_articulation_index`

Existing files generated before this commit **will not** have those keys. Re-run a clip to refresh its JSON.

---

## 5. What you should do

1. **Name files** with a 4-digit subject id (see section 3).
2. **Re-run** any session the dashboard should display with quality, vs-self, or articulation.
3. **Map** the new JSON keys on the dashboard:
   - `quality.flags` → capture badges
   - `vs_self.status` and `vs_self.metrics.*.delta` → “vs prior visits”
   - `markers.articulation_clarity` (this was previously computed but omitted from export — that is why some dashboards showed 0)
4. Quote paths with spaces in PowerShell:
   `.\venv\Scripts\python.exe claude_demo.py "recordings\AO 4-14-26 2.41PM - 0008.mp3" --patient-only`

First re-run for a subject will show `vs_self.status: no_baseline`. The next distinct visit for that same id will show `compared`.

---

## 6. Not in this drop

Still later, if we want them:

- Session-runner GUI
- Within-clip window timeline on the dashboard
- One-command batch over a folder of interviews

Emotional-state (traffic light, mix, volatility, confidence) and `--patient-only` gap collapse were already on `main` before this update.

---

## 7. Emotional stability over time (29 Oct)

Mark’s question: did this person’s stability get better or worse over a period — visit 1 vs visit 4, week 1 vs week 6?

JSON key: `stability_over_time`

| Field | Meaning |
|--------|---------|
| `current.volatility` | Stability *inside this session* (already computed) |
| `vs_first_visit` | This visit vs visit 1 |
| `vs_recent` | This visit vs the last 3 visits (moving point) |
| `vs_early_period` | This visit vs the first 7 days, when interview dates span 14+ days |
| `series` | One point per visit for the dashboard line |
| `direction` | `more_stable` / `more_volatile` / `unchanged` |

Lower volatility = more stable. History only includes sessions saved after this drop (or re-run). Same 4-digit subject id as vs-self.

---

## Questions this answers in a review

- “Is 55 bad?” → Compare to **this person’s** prior average, then check **quality flags**.
- “Why is pause/stress high on a long interview?” → Look at `patient_only` and `offmic_removed_sec`.
- “Where did articulatory clarity go?” → `markers.articulation_clarity` after a re-run.
- “Do we store left vs right ear?” → No. Filename suffix only.
- “Are they more stable than a month ago?” → `stability_over_time.direction` and `series`.
