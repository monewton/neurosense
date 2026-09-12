# Watchdawg + NeuroSense: Physician-Facing Anxiety/PTSD Progression Assessment

## Overview

This document describes how NeuroSense’s behavioral voice analysis can translate into physician-facing functionality when integrated with **Watchdawg** as a watch interface, specifically for **assessing anxiety and PTSD progression** over time.

---

## 1. What Physicians Get From This

- **Objective, repeatable metrics** alongside history and questionnaires (e.g., stress/arousal indicators, vocal engagement, consistency over time).
- **Trends over time** to see improvement, worsening, or stability (e.g., “stress index” or “behavioral score” week-over-week).
- **Context for anxiety/PTSD:** voice can reflect hyperarousal, avoidance (e.g., flat/low engagement), or response to triggers—useful as one input in a broader assessment.

**Bottom line:** NeuroSense becomes a source of continuous or periodic behavioral biomarkers that physicians use to **track anxiety/PTSD progression and treatment response**, not to replace clinical judgment.

---

## 2. How It Could Work on a Watch (Watchdawg)

### Capture

- **Short voice samples** (e.g., 30–60 seconds) initiated by the user on the watch (e.g., “Check-in” or “Quick assessment”) or prompted by the app at set times.
- Optional: **scheduled check-ins** (e.g., morning/evening) or **post-activity** (after exercise, exposure, or a stressful situation) to link metrics to context.
- Audio stays on-device for feature extraction; only derived metrics (and optionally summaries) need to be sent to the backend, preserving privacy.

### Processing (NeuroSense Logic)

- Run the same pipeline as in NeuroSense: energy, pitch variation, speech ratio, stress indicators (e.g., jitter, spectral flux), and a composite **stress/behavioral score**.
- Produce a small set of **watch-friendly metrics**, e.g.:
  - **Stress index** (0–100)
  - **Engagement/activation** (e.g., low/flat vs. more variable)
  - **Short-term trend** (e.g., “higher than your 7-day average”)

### Watch UI (Watchdawg)

- **Patient view:** Simple, non-clinical language (e.g., “Today’s check-in: moderate stress,” “Trend: improving this week”) and optional one-tap logging of context (e.g., “After work,” “After nightmare”).
- **Physician view (dashboard/report):**
  - Time series of stress index and engagement over days/weeks.
  - Optional tags: medication changes, therapy sessions, reported triggers.
  - So the physician sees **progression of anxiety/PTSD** as a trend line plus context, not raw audio.

### Integration With Watchdawg

- **Watchdawg** provides: trigger (when to record), context (optional labels, timestamps), and UI (patient + physician).
- **NeuroSense** provides: feature extraction and scoring (either on-device or via a small API that accepts short audio or precomputed features).
- **Backend:** store scores + timestamps + context and serve trend views and, if desired, summaries (e.g., “Last 2 weeks: stress index down 20%; engagement up”) for the physician.

---

## 3. Use Cases: Assessing Anxiety/PTSD Progression

| Use case | How it works |
|----------|----------------|
| **Baseline vs. now** | Compare current week’s stress/engagement to a baseline (e.g., post-intake) to show improvement or worsening. |
| **Treatment response** | After starting or changing medication/therapy, show whether stress index and engagement trends move in the expected direction over 2–4 weeks. |
| **Trigger/context correlation** | Let patients tag check-ins (e.g., “after trigger,” “after good sleep”); physicians see whether stress scores are higher in certain contexts, supporting behavioral and exposure planning. |
| **Relapse/early warning** | Sustained rise in stress index or drop in engagement over several days could be flagged for review (e.g., “Consider outreach or next appointment”). |

All of this is **adjunct to** diagnosis and clinical assessment—it gives physicians a **longitudinal, objective dimension** (behavioral/arousal trend) to assess anxiety/PTSD progression.

---

## 4. One-Paragraph Summary (For Stakeholders)

> We’re thinking of adding this to Watchdawg as an optional behavioral layer: the patient does short voice check-ins on the watch (e.g., 30–60 seconds, once or a few times per day or after relevant events). We run the same kind of analysis we use in NeuroSense—stress and engagement metrics from voice—and surface a simple stress index and trend on the watch for the patient, and a trend dashboard for the physician. That gives physicians an objective, longitudinal view of anxiety/PTSD progression (e.g., baseline vs. current, response to treatment, correlation with triggers) without replacing history or questionnaires. We’d keep capture on-device and only store and display the derived metrics and trends, so it fits into Watchdawg as a watch interface that supports assessment of anxiety and PTSD progression rather than replacing it.

---

## 5. How Doable Is This?

**Short answer: Very doable.** The core tech already exists in NeuroSense; the rest is integration, API, and (if Watchdawg isn’t built yet) watch app work.

| Piece | Doability | Notes |
|--------|-----------|--------|
| **Voice → stress/engagement metrics** | ✅ Done | NeuroSense already has feature extraction and stress scoring (energy, pitch, jitter, spectral flux, behavioral score). Works on 30–60 sec clips. |
| **Backend API** | 🟢 Straightforward | Expose the existing pipeline as a service: accept short audio (or precomputed features), return stress index + engagement + trend. Store time-series + context. Standard backend work. |
| **Trend storage & physician view** | 🟢 Straightforward | Store scores with timestamp and optional tags; serve time-series and simple summaries (e.g., “last 2 weeks down 20%”). No novel tech. |
| **Watch capture + UX** | 🟡 Depends on Watchdawg | If Watchdawg already has a watch app with mic and backend: adding a “voice check-in” flow and sending audio (or features) is incremental. If the watch app doesn’t exist yet, that’s the main build—but it’s Watchdawg’s scope, not NeuroSense’s. |
| **On-device vs. cloud** | 🟢 Flexible | Can run extraction on a backend (simplest) or, later, on-device (e.g., TensorFlow Lite / lightweight model) for privacy or offline. First version can be “record on watch → send to backend → get metrics back.” |
| **Clinical validation** | 🟡 Separate effort | Correlating trends with validated scales (e.g., GAD-7, PCL-5) or outcomes is important for physician trust but is a study/validation project, not a blocker for an MVP. |

**Summary for your colleague:**  
Technically, this is doable with what we have. The main variables are (1) how much of Watchdawg (watch app, backend, physician dashboard) already exists, and (2) whether we want an MVP (backend processing, simple trends) first and refine with validation later. No fundamental technical unknowns.

---

## 6. Caveats (Internal / Product)

- Voice is **one signal**; it should complement, not replace, clinical evaluation and self-report.
- Progression is best interpreted with **context** (medication, therapy, sleep, life events); Watchdawg’s tagging and timeline help with that.
- Clear **consent and transparency** with patients and physicians: what is recorded, what is analyzed, and how the physician will use the trends (e.g., “to track how you’re doing over time and adjust treatment”).

---

## 7. Next Steps (Optional)

- [ ] Define exact watch UX: when to prompt, how long to record, patient-facing labels.
- [ ] Specify API or on-device contract between Watchdawg and NeuroSense (audio vs. precomputed features).
- [ ] Design physician dashboard: which metrics, time ranges, and tags to show.
- [ ] Plan validation: correlate voice-derived trends with clinical outcomes or validated anxiety/PTSD scales where possible.
