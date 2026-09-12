"""
NeuroSense AI - Audio Analysis Test
Analyzes a recording to extract behavioral-like features.

Usage:
  python audio_analyzer.py
      Analyze the newest supported audio file under ./recordings/

  python audio_analyzer.py "E:\\path\\to\\clip.mp3"
      Analyze that file directly.

  python audio_analyzer.py --subject person1
      Analyze the newest recording for one subject.

  python audio_analyzer.py --subject person1 --tag "after work"
      Tag the session for trend correlation (e.g. triggers, time of day).

  python session_history.py --tags
      Compare average scores grouped by context tag.

  Compressed formats (MP3, M4A, AAC, Opus, WebM, …): requires
  `pip install librosa` and ffmpeg installed on PATH.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from audio_utils import configure_stdio, load_audio, pick_default_audio
from enhanced_features import (
    EnhancedFeatureExtractor,
    compute_voice_activity,
    print_feature_summary,
)
from session_history import (
    print_history,
    print_saved_session,
    print_trend_summary,
    resolve_subject_id,
    save_session,
)


def run_analysis(
    source_path: Path,
    audio_data: np.ndarray,
    sample_rate: int,
    *,
    subject_id: str | None = None,
    context_tag: str | None = None,
) -> None:
    print("📊 Audio File Info:")
    print(f"   Duration: {len(audio_data) / sample_rate:.2f} seconds")
    print(f"   Sample Rate: {sample_rate} Hz")
    print(f"   Total Samples: {len(audio_data)}")
    print()

    print("🔬 Extracting Behavioral Features...")
    print()

    extractor = EnhancedFeatureExtractor(sample_rate)
    features = extractor.extract_all_features(audio_data)
    print_feature_summary(features)

    print("📈 Creating visualization...")

    recordings_folder = Path("recordings")
    recordings_folder.mkdir(parents=True, exist_ok=True)

    frame_energies, threshold, speech_frames = compute_voice_activity(audio_data, sample_rate)
    hop_length = int(0.010 * sample_rate)

    fft = np.fft.fft(audio_data)
    frequencies = np.fft.fftfreq(len(fft), 1 / sample_rate)
    vocal_range = (frequencies >= 80) & (frequencies <= 1000)
    vocal_freqs = frequencies[vocal_range]
    vocal_magnitudes = np.abs(fft[vocal_range])

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    axes[0].plot(
        np.linspace(0, len(audio_data) / sample_rate, len(audio_data)),
        audio_data,
        color="blue",
        linewidth=0.5,
    )
    axes[0].set_title("Audio Waveform", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Time (seconds)")
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(True, alpha=0.3)

    if len(vocal_magnitudes) > 0:
        axes[1].plot(np.abs(vocal_freqs), vocal_magnitudes, color="green", linewidth=1)
        axes[1].set_title("Frequency Spectrum (Vocal Range)", fontsize=14, fontweight="bold")
        axes[1].set_xlabel("Frequency (Hz)")
        axes[1].set_ylabel("Magnitude")
        axes[1].grid(True, alpha=0.3)

    time_frames = np.arange(len(frame_energies)) * hop_length / sample_rate
    axes[2].fill_between(
        time_frames,
        0,
        frame_energies,
        where=speech_frames,
        color="orange",
        alpha=0.6,
        label="Voice Activity",
    )
    axes[2].plot(time_frames, frame_energies, color="red", linewidth=1, alpha=0.5)
    axes[2].axhline(y=threshold, color="black", linestyle="--", linewidth=1, label="Threshold")
    axes[2].set_title("Voice Activity Detection", fontsize=14, fontweight="bold")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].set_ylabel("Energy")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    plot_filename = recordings_folder / f"analysis_{source_path.stem}.png"
    plt.savefig(plot_filename, dpi=150, bbox_inches="tight")
    print(f"💾 Visualization saved: {plot_filename}")

    if matplotlib.get_backend().lower() == "agg":
        plt.close(fig)
    else:
        plt.show()

    subject_id = resolve_subject_id(subject_id, source_path)

    print_trend_summary(
        features,
        subject_id=subject_id,
        context_tag=context_tag,
    )
    saved = save_session(
        features,
        source_path,
        duration_sec=len(audio_data) / sample_rate,
        sample_rate=sample_rate,
        pipeline="analyzer",
        subject_id=subject_id,
        context_tag=context_tag,
    )
    print_saved_session(saved)

    print("=" * 60)
    print("✅ Analysis Complete!")
    print()
    print("Next step: python claude_demo.py --file", source_path)
    print("View history: python session_history.py")
    print("=" * 60)


def main() -> None:
    configure_stdio()

    parser = argparse.ArgumentParser(
        description="Analyze an audio recording (MP3, M4A, FLAC, WAV, …).",
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        default=None,
        help="Path to audio file. If omitted, uses newest supported file in ./recordings/",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show recent session history and exit",
    )
    parser.add_argument(
        "--tag",
        metavar="LABEL",
        help='Optional context label (e.g. "after work", "morning check-in")',
    )
    parser.add_argument(
        "--subject",
        metavar="ID",
        help="Subject id for per-person tracking (e.g. person1, person2)",
    )
    args = parser.parse_args()

    if args.history:
        print_history(subject_id=args.subject, context_tag=args.tag)
        return

    print("=" * 60)
    print("NeuroSense AI - Audio Analysis Test")
    print("=" * 60)
    print()

    try:
        if args.audio_file:
            source_path = Path(args.audio_file)
        else:
            source_path = pick_default_audio(subject_id=args.subject)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print('   Pass a file: python audio_analyzer.py "path\\to\\file.mp3"')
        if args.subject:
            print(f'   Or record first: python simple_recorder.py --subject {args.subject}')
        sys.exit(1)

    resolved_subject = resolve_subject_id(args.subject, source_path)

    print(f"📂 Analyzing: {source_path}")
    if resolved_subject:
        print(f"👤 Subject: {resolved_subject}")
    if args.tag:
        print(f"🏷️  Context tag: {args.tag}")
    print()

    try:
        audio_data, sample_rate = load_audio(source_path)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    run_analysis(
        source_path,
        audio_data,
        sample_rate,
        subject_id=resolved_subject,
        context_tag=args.tag,
    )


if __name__ == "__main__":
    main()
