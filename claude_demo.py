"""
NeuroSense AI - Complete Claude AI Demo
Records audio (or uses an existing file), extracts features, and gets Claude AI interpretation.

Usage:
  python claude_demo.py --file recordings/test_recording.wav --tag "after work"
      Analyze an existing recording through Claude with a context tag.

  python claude_demo.py
      Interactive: record a new clip, then analyze with Claude.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from alert_sender import send_alert, should_send_alert
from audio_utils import configure_stdio, load_audio, pick_default_audio
from claude_analyzer import ClaudeBehavioralAnalyzer
from enhanced_features import (
    EnhancedFeatureExtractor,
    prepare_scoring_audio,
    print_feature_summary,
    print_offmic_pause_notice,
)
from emotional_state import print_emotional_state, windowed_emotional_state
from session_history import (
    next_recording_path,
    print_history,
    print_saved_session,
    print_trend_summary,
    resolve_subject_id,
    save_session,
)


class CompleteBehavioralDemo:
    """Complete demo: Capture → Analyze → Claude Interpretation"""

    def __init__(self):
        self.sample_rate = 44100
        self.recordings_folder = Path("recordings")
        self.recordings_folder.mkdir(exist_ok=True)
        self.extractor = EnhancedFeatureExtractor(self.sample_rate)

    def record_audio(self, duration=10, scenario="normal", *, subject_id: str | None = None):
        """Record audio sample from the microphone."""
        print("\n" + "=" * 70)
        print("🎤 STEP 1: BEHAVIORAL DATA CAPTURE")
        print("=" * 70)
        print()
        print("📋 Recording Parameters:")
        if subject_id:
            print(f"   Subject: {subject_id}")
        print(f"   Scenario: {scenario.upper()}")
        print(f"   Duration: {duration} seconds")
        print(f"   Quality: CD-grade (44.1kHz)")
        print()

        input("Press ENTER to begin recording...")

        print("\n🎬 Recording in: 3... 2... 1...")
        print("🔴 RECORDING NOW\n")

        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float64",
        )
        sd.wait()

        print("✅ Recording captured!\n")

        if subject_id:
            filename = next_recording_path(subject_id, self.recordings_folder)
            print(f"💾 Saving as: {filename}")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.recordings_folder / f"claude_demo_{scenario}_{timestamp}.wav"

        sf.write(filename, recording, self.sample_rate)

        return recording.flatten(), filename

    def load_file(self, path: Path, *, subject_id: str | None = None) -> tuple[np.ndarray, Path]:
        """Load an existing audio file for analysis."""
        print("\n" + "=" * 70)
        print("📂 STEP 1: LOAD EXISTING RECORDING")
        print("=" * 70)
        print()
        print(f"   File: {path}")
        resolved_subject = resolve_subject_id(subject_id, path)
        if resolved_subject:
            print(f"   Subject: {resolved_subject}")
        audio_data, sample_rate = load_audio(path)
        self.extractor = EnhancedFeatureExtractor(sample_rate)
        print(f"   Duration: {len(audio_data) / sample_rate:.2f} seconds")
        print(f"   Sample Rate: {sample_rate} Hz")
        print()
        return audio_data, path

    def extract_features(
        self,
        audio_data: np.ndarray,
        *,
        patient_only: bool = False,
    ) -> dict:
        """Extract behavioral features from audio."""
        print("=" * 70)
        print("📊 STEP 2: FEATURE EXTRACTION")
        print("=" * 70)
        print()
        print("🔬 Analyzing audio patterns...")
        print()

        scoring_audio, pause_stats = prepare_scoring_audio(
            audio_data, self.extractor.sample_rate, patient_only=patient_only
        )
        print_offmic_pause_notice(pause_stats, patient_only=patient_only)

        emotion = windowed_emotional_state(scoring_audio, self.extractor.sample_rate)
        features = emotion["features"]
        features.update(pause_stats)
        print("✅ Feature Extraction Complete\n")
        print_feature_summary(features)
        print_emotional_state(emotion)
        return features

    async def get_claude_analysis(self, features: dict) -> dict:
        """Get Claude AI interpretation."""
        print("=" * 70)
        print("🤖 STEP 3: CLAUDE AI INTERPRETATION")
        print("=" * 70)
        print()

        analyzer = ClaudeBehavioralAnalyzer()
        try:
            await analyzer.initialize()
            return await analyzer.analyze_behavioral_data(features)
        finally:
            await analyzer.close()

    def _save_and_show_trends(
        self,
        features: dict,
        source: Path,
        *,
        audio_data: np.ndarray,
        sample_rate: int,
        scenario: str | None,
        analysis: dict | None,
        subject_id: str | None = None,
        context_tag: str | None = None,
    ) -> None:
        subject_id = resolve_subject_id(subject_id, source)
        print_trend_summary(
            features,
            subject_id=subject_id,
            context_tag=context_tag,
        )
        saved = save_session(
            features,
            source,
            duration_sec=len(audio_data) / sample_rate,
            sample_rate=sample_rate,
            pipeline="claude_demo",
            subject_id=subject_id,
            scenario=scenario,
            context_tag=context_tag,
            claude_analysis=analysis,
        )
        print_saved_session(saved)

    def _print_analysis(
        self,
        analysis: dict,
        source: Path,
        *,
        features: dict,
        audio_data: np.ndarray,
        sample_rate: int,
        scenario: str | None = None,
        subject_id: str | None = None,
        context_tag: str | None = None,
    ) -> None:
        if "error" in analysis:
            print("\n❌ CLAUDE ANALYSIS ERROR:")
            print(f"   {analysis['error']}")
            if "details" in analysis:
                print(f"   {analysis['details']}")
            return

        print("\n" + "=" * 70)
        print("🤖 CLAUDE AI BEHAVIORAL ANALYSIS")
        print("=" * 70)
        print()
        print(analysis["raw_analysis"])
        print()
        print("=" * 70)
        print("📋 SUMMARY")
        print("=" * 70)
        print(f"   Status: {analysis.get('status', 'N/A')}")
        print(f"   Confidence: {analysis.get('confidence', 'N/A')}")
        print(f"   Source: {source}")
        resolved_subject = resolve_subject_id(subject_id, source)
        if resolved_subject:
            print(f"   Subject: {resolved_subject}")
        if context_tag:
            print(f"   Context tag: {context_tag}")
        print()

        self._save_and_show_trends(
            features,
            source,
            audio_data=audio_data,
            sample_rate=sample_rate,
            scenario=scenario,
            analysis=analysis,
            subject_id=subject_id,
            context_tag=context_tag,
        )

        if should_send_alert(analysis.get("status", "")):
            send_alert(
                analysis["status"],
                summary_details={
                    "confidence": analysis.get("confidence", "N/A"),
                    "timestamp": analysis.get("timestamp", ""),
                    "raw_analysis": analysis.get("raw_analysis", ""),
                },
            )

    async def run_from_file(
        self,
        path: Path,
        *,
        subject_id: str | None = None,
        context_tag: str | None = None,
        patient_only: bool = False,
    ) -> None:
        """Run the full pipeline on an existing recording."""
        audio_data, source = self.load_file(path, subject_id=subject_id)
        sample_rate = self.extractor.sample_rate
        resolved_subject = resolve_subject_id(subject_id, source)
        features = self.extract_features(audio_data, patient_only=patient_only)
        analysis = await self.get_claude_analysis(features)
        self._print_analysis(
            analysis,
            source,
            features=features,
            audio_data=audio_data,
            sample_rate=sample_rate,
            subject_id=resolved_subject,
            context_tag=context_tag,
        )

    async def run_complete_demo(
        self,
        duration=10,
        scenario="normal",
        *,
        subject_id: str | None = None,
        context_tag: str | None = None,
    ) -> None:
        """Run the full demo: record → extract → Claude."""
        recording, filename = self.record_audio(
            duration=duration,
            scenario=scenario,
            subject_id=subject_id,
        )
        resolved_subject = resolve_subject_id(subject_id, filename)
        features = self.extract_features(recording)
        analysis = await self.get_claude_analysis(features)
        self._print_analysis(
            analysis,
            filename,
            features=features,
            audio_data=recording,
            sample_rate=self.sample_rate,
            scenario=scenario,
            subject_id=resolved_subject,
            context_tag=context_tag,
        )


async def main() -> None:
    configure_stdio()

    parser = argparse.ArgumentParser(
        description="Record or load audio, extract features, and get Claude AI analysis.",
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Analyze an existing audio file instead of recording",
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
    parser.add_argument(
        "--patient-only",
        action="store_true",
        help=(
            "Interview capture with no interviewer on the mic: collapse silences "
            "longer than 2s (off-mic turns) before scoring."
        ),
    )
    args = parser.parse_args()

    if args.history:
        print_history(subject_id=args.subject, context_tag=args.tag)
        return

    demo = CompleteBehavioralDemo()

    if args.file:
        await demo.run_from_file(
            Path(args.file),
            subject_id=args.subject,
            context_tag=args.tag,
            patient_only=args.patient_only,
        )
        return

    print("\n" + "=" * 70)
    print("                    🧠 NEUROSENSE AI - COMPLETE DEMO")
    print("              Record → Extract Features → Claude AI Analysis")
    print("=" * 70)
    print()
    print("   Tip: analyze an existing file with:")
    print("        python claude_demo.py --subject person1 --file recordings\\person1\\recording_001.wav")
    print()
    print("   [1] Normal/Baseline (10 sec)")
    print("   [2] Stressed (10 sec)")
    print("   [3] Fatigued (10 sec)")
    print("   [4] Custom duration")
    print()
    choice = input("Select scenario (1-4) [default 1]: ").strip() or "1"
    scenario = {"1": "normal", "2": "stressed", "3": "fatigued"}.get(choice, "normal")

    if choice == "4":
        duration_input = input("Duration in seconds [10]: ").strip()
        duration = int(duration_input) if duration_input.isdigit() else 10
    else:
        duration = 10

    context_tag = args.tag
    if not context_tag:
        tag_input = input('Context tag (optional, e.g. "after work") [skip]: ').strip()
        context_tag = tag_input or None

    subject_id = args.subject
    if not subject_id:
        subject_input = input("Subject id (e.g. person1) [skip]: ").strip()
        subject_id = subject_input or None

    await demo.run_complete_demo(
        duration=duration,
        scenario=scenario,
        subject_id=subject_id,
        context_tag=context_tag,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelled by user")
    except FileNotFoundError as e:
        print(f"\n\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nMake sure:")
        print("  • You have a .env file with CLAUDE_API_KEY")
        print("  • Dependencies are installed: pip install -r requirements.txt")
        print("  • Your API key is valid")
