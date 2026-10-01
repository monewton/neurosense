"""
NeuroSense AI — Emotional-state inference from acoustic proxies.

Maps acoustic feature dicts into an affective-computing readout that answers:
  - What emotional state is inferred? (stress / sadness / anger / neutral)
  - How strong is it? (0–5 level + green/yellow/red)
  - Are emotions mixed or blended?
  - How volatile is the state within the clip?
  - How confident are we? (confidence drops when volatility/mixing is high)

This layer sits *on top of* enhanced_features. Acoustic markers remain the
measurable proxies; this module is the clinical/psychological interpretation
Mark/SOCOM framing requires (state change, treatment tracking, stability).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from enhanced_features import EnhancedFeatureExtractor

EMOTIONS = ("stress", "sadness", "anger", "neutral")


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _level_0_5(activation: float) -> int:
    """Map 0–1 activation to discrete 0–5 severity/presence level."""
    if activation < 0.08:
        return 0
    return int(max(1, min(5, round(activation * 5))))


def _traffic_light(emotion: str, level: int) -> str:
    """green/yellow/red for actionable triage (neutral stays green/yellow)."""
    if emotion == "neutral":
        return "green" if level <= 3 else "yellow"
    if level <= 1:
        return "green"
    if level <= 3:
        return "yellow"
    return "red"


def compute_emotion_activations(features: dict) -> dict[str, float]:
    """
    Infer relative emotional activations (0–1) from acoustic proxies.

    Heuristic, interpretable mapping — not a black-box classifier.
    Tunable as clinical validation data arrives.
    """
    stress_lvl = float(features.get("stress_level", 0)) / 100.0
    pitch_var = float(features.get("pitch_variation", 0))
    jitter = float(features.get("jitter", 0))
    shimmer = float(features.get("shimmer", 0))
    tension = float(features.get("tension", 0))
    rate = float(features.get("speaking_rate", 0))
    rms = float(features.get("rms_energy", 0))
    pta = float(features.get("peak_to_average_ratio", features.get("dynamic_range", 0)))
    pause = float(features.get("pause_ratio", 0))
    emphasis = float(features.get("prosody_emphasis", 0))
    slur = float(features.get("slur_index", 0))
    contour = abs(float(features.get("prosody_contour_slope", 0)))
    f0 = float(features.get("f0_mean", features.get("pitch_mean", 0)))

    # --- Stress: arousal / tension / instability ---
    stress = (
        0.35 * stress_lvl
        + 0.20 * _clamp01(pitch_var / 0.35)
        + 0.15 * _clamp01(jitter / 0.8)
        + 0.10 * _clamp01(shimmer / 0.4)
        + 0.10 * _clamp01(tension / 1.5)
        + 0.10 * _clamp01((rate - 2.0) / 3.0)
    )

    # --- Anger: high energy, punchy dynamics, fast, tense ---
    anger = (
        0.25 * _clamp01(rms / 0.08)
        + 0.20 * _clamp01(pta / 12.0)
        + 0.20 * _clamp01(emphasis / 4.0)
        + 0.15 * _clamp01((rate - 3.0) / 3.0)
        + 0.10 * _clamp01(tension / 1.5)
        + 0.10 * _clamp01(1.0 - pause)
    )

    # --- Sadness: low energy, slow, pause-heavy, flatter, slurred ---
    sadness = (
        0.25 * _clamp01(1.0 - rms / 0.05)
        + 0.20 * _clamp01(pause / 0.7)
        + 0.15 * _clamp01((3.0 - rate) / 3.0)
        + 0.15 * _clamp01(slur)
        + 0.10 * _clamp01(1.0 - emphasis / 3.0)
        + 0.10 * _clamp01(1.0 - min(f0, 200.0) / 200.0)  # lower F0 leans sad
        + 0.05 * _clamp01(1.0 - contour / 20.0)  # flatter contour
    )

    # --- Neutral / mood baseline: mid energy, steady rate, low instability ---
    mid_rate = 1.0 - abs(rate - 3.0) / 3.0
    mid_energy = 1.0 - abs(rms - 0.03) / 0.05
    stable = 1.0 - _clamp01(pitch_var / 0.35)
    neutral = (
        0.35 * _clamp01(mid_rate)
        + 0.25 * _clamp01(mid_energy)
        + 0.25 * _clamp01(stable)
        + 0.15 * _clamp01(1.0 - stress_lvl)
    )

    raw = {
        "stress": _clamp01(stress),
        "sadness": _clamp01(sadness),
        "anger": _clamp01(anger),
        "neutral": _clamp01(neutral),
    }

    # Soft competition: boost relative contrast without hard winner-take-all
    total = sum(raw.values()) + 1e-9
    return {k: float(v / total) for k, v in raw.items()}


def _activation_entropy(activations: dict[str, float]) -> float:
    vals = np.array([activations[e] for e in EMOTIONS], dtype=float)
    vals = vals / (vals.sum() + 1e-12)
    vals = vals[vals > 1e-12]
    return float(-np.sum(vals * np.log(vals + 1e-12)))


def infer_emotional_state(
    features: dict,
    *,
    window_activations: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
    """
    Full affective readout from a session feature dict (+ optional window series).
    """
    activations = compute_emotion_activations(features)
    ranked = sorted(activations.items(), key=lambda kv: kv[1], reverse=True)
    primary, primary_act = ranked[0]
    secondary, secondary_act = ranked[1]

    level = _level_0_5(primary_act)
    status_color = _traffic_light(primary, level)

    # Mixed / blend: second emotion is competitively close
    mixed = secondary_act >= 0.22 and secondary_act >= 0.65 * primary_act
    blend = None
    if mixed:
        blend = f"{primary}+{secondary}"

    # Volatility from within-clip window activations (0–1 scale) → V̄
    if window_activations and len(window_activations) >= 2:
        mat = np.array([[w.get(e, 0.0) for e in EMOTIONS] for w in window_activations])
        channel_vol = float(np.mean(np.std(mat, axis=0)))
        dom_idx = np.argmax(mat, axis=1)
        flips = float(np.mean(dom_idx[1:] != dom_idx[:-1])) if len(dom_idx) > 1 else 0.0
        volatility = _clamp01(0.6 * channel_vol * 3.0 + 0.4 * flips)
        volatility_source = "within_clip_windows"
    else:
        volatility = _clamp01(
            0.4 * float(features.get("pitch_variation", 0)) / 0.35
            + 0.3 * float(features.get("jitter", 0)) / 0.8
            + 0.3 * float(features.get("energy_variance", 0)) / 0.002
        )
        volatility_source = "feature_instability_proxy"

    # Mark / SOCOM confidence components (0–1), then weighted sum:
    #   C_vol = 1 - V̄
    #   C = 0.40*C_distance + 0.25*C_dominance + 0.15*C_mixed + 0.20*C_vol
    max_ent = float(np.log(len(EMOTIONS)))
    ent = _activation_entropy(activations)
    c_distance = _clamp01(1.0 - ent / max_ent)  # how centered / peaked the activation is
    c_dominance = _clamp01((primary_act - secondary_act) / (primary_act + 1e-9))
    c_mixed = 0.0 if mixed else 1.0  # penalty when emotions compete
    c_vol = _clamp01(1.0 - volatility)

    confidence = 100.0 * (
        0.40 * c_distance + 0.25 * c_dominance + 0.15 * c_mixed + 0.20 * c_vol
    )
    confidence = float(round(max(0.0, min(100.0, confidence)), 1))

    interpretation = _plain_language(
        primary, secondary, level, status_color, mixed, blend, volatility, confidence
    )

    return {
        "emotional_activations": {k: round(v, 4) for k, v in activations.items()},
        "primary_emotion": primary,
        "secondary_emotion": secondary,
        "emotion_level": level,
        "traffic_light": status_color,
        "mixed_emotion": mixed,
        "emotion_blend": blend,
        "neutral_baseline": round(activations["neutral"], 4),
        "volatility": round(volatility, 4),
        "volatility_source": volatility_source,
        "confidence": confidence,
        "confidence_components": {
            "C_distance": round(c_distance, 4),
            "C_dominance": round(c_dominance, 4),
            "C_mixed": round(c_mixed, 4),
            "C_vol": round(c_vol, 4),
            "weights": {"distance": 0.40, "dominance": 0.25, "mixed": 0.15, "vol": 0.20},
        },
        "interpretation": interpretation,
    }


def _plain_language(
    primary: str,
    secondary: str,
    level: int,
    color: str,
    mixed: bool,
    blend: str | None,
    volatility: float,
    confidence: float,
) -> str:
    vol_word = "stable" if volatility < 0.25 else "moderately volatile" if volatility < 0.5 else "highly volatile"
    mix_bit = f" Mixed presentation ({blend})." if mixed and blend else ""
    meaning = {
        "stress": "elevated stress / arousal markers",
        "sadness": "low-energy / withdrawn affective markers",
        "anger": "high-arousal / irritation-compatible markers",
        "neutral": "near-baseline / regulated mood markers",
    }[primary]
    return (
        f"Inferred state: {primary} at level {level}/5 ({color}). "
        f"Acoustic pattern suggests {meaning}.{mix_bit} "
        f"Within-clip state appears {vol_word} (volatility={volatility:.2f}). "
        f"Confidence={confidence:.0f}/100 "
        f"(confidence falls when volatility is high or emotions compete)."
    )


def windowed_emotional_state(
    audio_data: np.ndarray,
    sample_rate: int,
    *,
    window_sec: float = 30.0,
    hop_sec: float = 15.0,
    min_windows: int = 2,
    max_windows: int = 12,
) -> dict[str, Any]:
    """
    Full-clip features + within-call volatility from sliding windows.

    For short clips (< ~2 windows), falls back to single-pass inference.
    Long calls are sampled into at most `max_windows` segments for speed.
    """
    audio_data = np.asarray(audio_data, dtype=float)
    extractor = EnhancedFeatureExtractor(sample_rate)
    full_features = extractor.extract_all_features(audio_data)

    n = len(audio_data)
    duration = n / sample_rate if sample_rate else 0.0

    # Adaptive windows for long telephony files
    if duration > 180:
        window_sec = max(window_sec, duration / max_windows)
        hop_sec = window_sec * 0.75

    win = int(window_sec * sample_rate)
    hop = max(1, int(hop_sec * sample_rate))
    window_acts: list[dict[str, float]] = []

    if win > 0 and n >= win * min_windows:
        starts = list(range(0, n - win + 1, hop))
        if len(starts) > max_windows:
            idx = np.linspace(0, len(starts) - 1, max_windows, dtype=int)
            starts = [starts[i] for i in idx]
        for start in starts:
            chunk = audio_data[start : start + win]
            feats = extractor.extract_all_features(chunk)
            window_acts.append(compute_emotion_activations(feats))

    state = infer_emotional_state(full_features, window_activations=window_acts or None)
    # Attach compact emotion fields onto features for history / Claude
    full_features["primary_emotion"] = state["primary_emotion"]
    full_features["secondary_emotion"] = state["secondary_emotion"]
    full_features["emotion_level"] = state["emotion_level"]
    full_features["emotion_traffic_light"] = state["traffic_light"]
    full_features["emotion_volatility"] = state["volatility"]
    full_features["emotion_confidence"] = state["confidence"]
    full_features["mixed_emotion"] = state["mixed_emotion"]
    full_features["emotion_blend"] = state["emotion_blend"]
    full_features["emotional_activations"] = state["emotional_activations"]
    full_features["emotion_interpretation"] = state["interpretation"]

    state["features"] = full_features
    state["window_count"] = len(window_acts)
    return state


def print_emotional_state(state: dict[str, Any]) -> None:
    """CLI block answering Mark's 'What does this mean?' question."""
    acts = state.get("emotional_activations", {})
    print("Emotional state (acoustic-proxy inference):")
    print(
        f"   Activations — stress {acts.get('stress', 0):.2f} | "
        f"sadness {acts.get('sadness', 0):.2f} | "
        f"anger {acts.get('anger', 0):.2f} | "
        f"neutral {acts.get('neutral', 0):.2f}"
    )
    print(
        f"   Primary: {state.get('primary_emotion')}  "
        f"level {state.get('emotion_level')}/5  "
        f"[{state.get('traffic_light')}]"
    )
    if state.get("mixed_emotion"):
        print(f"   Mixed / blend: {state.get('emotion_blend')}")
    print(
        f"   Volatility: {state.get('volatility'):.3f}  "
        f"(C_vol={state.get('confidence_components', {}).get('C_vol', 'n/a')}, "
        f"{state.get('volatility_source')}, windows={state.get('window_count', 0)})"
    )
    print(f"   Confidence: {state.get('confidence'):.1f}/100")
    comps = state.get("confidence_components") or {}
    if comps:
        print(
            f"   Confidence parts — distance {comps.get('C_distance'):.2f} | "
            f"dominance {comps.get('C_dominance'):.2f} | "
            f"mixed {comps.get('C_mixed'):.2f} | "
            f"vol {comps.get('C_vol'):.2f}"
        )
    print(f"   Meaning: {state.get('interpretation')}")
    print()
