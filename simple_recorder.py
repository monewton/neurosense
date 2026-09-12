"""
NeuroSense AI - Simple Audio Recorder Test
Records a short clip and saves it under recordings/<subject>/recording_NNN.wav
"""

from __future__ import annotations

import argparse

import numpy as np
import sounddevice as sd
import soundfile as sf

from audio_utils import configure_stdio
from session_history import next_recording_path, normalize_subject_id


def main() -> None:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Record a short test audio clip.")
    parser.add_argument(
        "--subject",
        metavar="ID",
        required=True,
        help="Subject id (e.g. person1, person2)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Recording length in seconds (default: 5)",
    )
    args = parser.parse_args()

    subject_id = normalize_subject_id(args.subject)
    if not subject_id:
        raise SystemExit("Invalid subject id.")

    duration = max(1, args.duration)
    sample_rate = 44100

    print("=" * 60)
    print("NeuroSense AI - Audio Recording Test")
    print("=" * 60)
    print()
    print(f"👤 Subject: {subject_id}")
    print(f"🎤 Recording for {duration} seconds...")
    print("📢 Say something! (counting down...)")
    print()

    for i in range(3, 0, -1):
        print(f"   {i}...")
        sd.sleep(1000)

    print("   🔴 RECORDING NOW!")
    print()

    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float64",
    )
    sd.wait()

    filename = next_recording_path(subject_id)
    sf.write(filename, recording, sample_rate)

    print("✅ Recording complete!")
    print(f"💾 Saved to: {filename}")
    print()
    print("📊 Recording Analysis:")
    print(f"   Duration: {duration} seconds")
    print(f"   Sample Rate: {sample_rate} Hz")
    print(f"   Total Samples: {len(recording)}")
    print(f"   Peak Volume: {np.max(np.abs(recording)):.3f}")
    print(f"   Average Volume: {np.mean(np.abs(recording)):.3f}")
    print()

    if np.max(np.abs(recording)) > 0.01:
        print("✅ SUCCESS! Audio was captured.")
        print("   Your microphone is working!")
    else:
        print("⚠️  WARNING: Very quiet or no audio detected.")
        print("   Check your microphone settings.")

    print()
    print("=" * 60)
    print("Next step:")
    print(f"  python audio_analyzer.py --subject {subject_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
