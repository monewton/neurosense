# NeuroSense AI — Voice Analysis Batch Summary

**Batch date:** July 2, 2026  
**Source folder:** `D:\Neurosense AI\audio`  
**Files analyzed:** 9 MP3 recordings (3 subjects: AO, MD, DW)  
**Pipeline:** Feature extraction → stress/behavioral scores → Claude AI → session history  

---

## Executive summary

All 9 recordings were processed successfully. Most sessions scored **65/75** (behavioral/stress) with **Good** algorithmic status. **One outlier** — **DW 5-18-26** — scored **52/90**, the only session with stress at **90** and behavioral below **55**. Claude flagged **8 of 9** sessions as *Needs Attention*; **AO 4-15-26** was the sole *Good* classification.

Recordings are **long-form** (~10–14 minutes each, 8 kHz telephony quality), not short check-in clips.

---

## Results by file

| File | Subject | Behavioral | Stress | Algo status | Claude status |
|------|---------|------------|--------|-------------|---------------|
| AO 4-14-26 2.41PM - 008 | ao | 65 | 75 | Good | Needs Attention |
| AO 4-15-26 12.50PM - 009 | ao | 65 | 75 | Good | **Good** |
| AO 4-16-26 2.47PM - 003 | ao | 65 | 75 | Good | Needs Attention |
| AO 4-17-26 8.39AM - 006 | ao | **70** | 75 | Good | Needs Attention |
| MD 4-29-26 2.55PM - 008 | md | **70** | 75 | Good | Needs Attention |
| **DW 5-18-26 3.28PM - 010** | **dw** | **52** | **90** | **Fair** | **Needs Attention** |
| DW 5-28-26 8.27AM - 018 | dw | 65 | 75 | Good | Needs Attention |
| DW 5-29-26 8.13AM - 008 | dw | 65 | 75 | Good | Needs Attention |
| DW 6-11-26 11.28AM -008 | dw | 65 | 75 | Good | Needs Attention |

---

## Subject averages

| Subject | Sessions | Avg behavioral | Avg stress | Notes |
|---------|----------|----------------|------------|-------|
| **AO** | 4 | 66.2 | 75.0 | Stable; best score 70 (4-17) |
| **MD** | 1 | 70.0 | 75.0 | Single session — no trend yet |
| **DW** | 4 | 61.8 | 78.8 | **5-18 outlier** pulls averages down |

---

## DW outlier highlight

**DW 5-18-26 3.28PM - 010.mp3** is the only file with materially different metrics:

- Stress **+11.2** above DW average (90 vs 78.8)
- Behavioral **−9.8** below DW average (52 vs 61.8)
- Speaking rate **4.31** syllables/sec (fastest in batch — contributes to stress score)
- Email alert sent; full Claude narrative in `DW_5-18-26_Claude_Narrative.md`

**Claude one-liner:** *"Not clearly pathological but not within a healthy high-function range — the 52/100 composite score is the primary flag."*

---

## Technical notes

- Claude model updated to `claude-sonnet-4-6` (previous model retired June 2026)
- Sessions stored in `data/neurosense_history.db` per subject
- Charts saved under `recordings/analysis_*.png`
- Full batch log: `reports/claude_batch_20260702_fixed.txt`

---

## Disclaimer

NeuroSense metrics and AI interpretations are **exploratory** and **not validated diagnostic tools**. Scores reflect acoustic features from voice recordings and should be interpreted by qualified personnel alongside clinical observation and subject history. Not for standalone medical decisions.

---

*NeuroSense AI — Halberd Corporation*
