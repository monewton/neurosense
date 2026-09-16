"""Compact session-results JSON for handoff (e.g. Amy / Connect Converse)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


RESULTS_SCHEMA = "neurosense.session_results.v1"


def _json_number(value: Any, *, ndigits: int | None = 4) -> float | int:
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    number = float(value)
    if ndigits is None:
        return number
    return round(number, ndigits)


def _g(features: dict, key: str, default: Any = 0) -> Any:
    return features.get(key, default)


def _behavioral_status(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Low Activity"


def build_session_results(
    features: dict,
    source_path: Path | str,
    *,
    duration_sec: float,
    sample_rate: int,
    subject_id: str | None = None,
    context_tag: str | None = None,
    pipeline: str = "analyzer",
    claude_analysis: dict | None = None,
    session: dict | None = None,
) -> dict[str, Any]:
    """
    Curated results payload — composites + emotional state + compact markers.

    More efficient than dumping the full feature dict: this is what the console
    shows and what Amy needs to display (scores, traffic light, optional narrative).
    """
    source = Path(source_path)
    behavioral = int(_g(features, "behavioral_score", 0))
    stress = int(_g(features, "stress_level", 0))

    payload: dict[str, Any] = {
        "schema": RESULTS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "file": source.name,
            "path": str(source),
            "subject_id": subject_id,
            "context_tag": context_tag,
            "duration_sec": _json_number(duration_sec, ndigits=2),
            "sample_rate": int(sample_rate),
            "pipeline": pipeline,
            "patient_only": bool(_g(features, "pause_collapse_applied", False)),
        },
        "composites": {
            "behavioral_score": behavioral,
            "stress_level": stress,
            "vocal_stability": _json_number(_g(features, "vocal_stability", 0), ndigits=3),
            "speech_ratio": _json_number(_g(features, "speech_ratio", 0), ndigits=4),
            "status": _behavioral_status(behavioral),
        },
        "emotional_state": {
            "primary": _g(features, "primary_emotion", None),
            "secondary": _g(features, "secondary_emotion", None),
            "level": _g(features, "emotion_level", None),
            "traffic_light": _g(features, "emotion_traffic_light", None),
            "mixed": bool(_g(features, "mixed_emotion", False)),
            "blend": _g(features, "emotion_blend", None),
            "volatility": _json_number(_g(features, "emotion_volatility", 0), ndigits=4),
            "confidence": _json_number(_g(features, "emotion_confidence", 0), ndigits=1),
            "activations": _g(features, "emotional_activations", {}),
            "interpretation": _g(features, "emotion_interpretation", None),
        },
        "markers": {
            "f0_mean_hz": _json_number(
                _g(features, "f0_mean", _g(features, "pitch_mean", 0)), ndigits=1
            ),
            "pitch_variation": _json_number(_g(features, "pitch_variation", 0), ndigits=4),
            "speaking_rate": _json_number(_g(features, "speaking_rate", 0), ndigits=2),
            "speaking_rate_wpm": _json_number(_g(features, "speaking_rate_wpm", 0), ndigits=1),
            "rms_energy": _json_number(_g(features, "rms_energy", 0), ndigits=4),
            "pause_ratio": _json_number(_g(features, "pause_ratio", 0), ndigits=4),
            "jitter": _json_number(_g(features, "jitter", 0), ndigits=4),
            "shimmer": _json_number(_g(features, "shimmer", 0), ndigits=4),
            "tension": _json_number(_g(features, "tension", 0), ndigits=3),
        },
    }

    if _g(features, "pause_collapse_applied", False):
        payload["source"]["offmic_gaps_collapsed"] = int(_g(features, "n_gaps_collapsed", 0))
        payload["source"]["offmic_removed_sec"] = _json_number(
            _g(features, "removed_sec", 0), ndigits=1
        )

    if session:
        payload["session"] = {
            "id": session.get("id"),
            "subject_id": session.get("subject_id"),
            "recording_number": session.get("recording_number"),
        }

    if claude_analysis and "error" not in claude_analysis:
        payload["claude"] = {
            "status": claude_analysis.get("status"),
            "confidence": claude_analysis.get("confidence"),
            "model": claude_analysis.get("ai_model"),
            "narrative": claude_analysis.get("raw_analysis"),
        }
    else:
        payload["claude"] = None

    return payload


def write_session_results_json(
    features: dict,
    source_path: Path | str,
    *,
    duration_sec: float,
    sample_rate: int,
    subject_id: str | None = None,
    context_tag: str | None = None,
    pipeline: str = "analyzer",
    claude_analysis: dict | None = None,
    session: dict | None = None,
    output_dir: Path | str = "recordings",
) -> Path:
    """Write `analysis_<stem>.json` next to the PNG chart. Returns the path."""
    source = Path(source_path)
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    out_path = folder / f"analysis_{source.stem}.json"
    payload = build_session_results(
        features,
        source,
        duration_sec=duration_sec,
        sample_rate=sample_rate,
        subject_id=subject_id,
        context_tag=context_tag,
        pipeline=pipeline,
        claude_analysis=claude_analysis,
        session=session,
    )
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path
