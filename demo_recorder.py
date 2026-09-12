"""
NeuroSense AI - Live Demo Recording Tool
Polished for client demonstrations and presentations
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import os
import time

class DemoRecorder:
    """Professional recording tool for live demonstrations"""
    
    def __init__(self):
        self.sample_rate = 44100
        self.recordings_folder = 'recordings'
        
        # Create recordings folder
        if not os.path.exists(self.recordings_folder):
            os.makedirs(self.recordings_folder)
    
    def show_header(self):
        """Display professional header"""
        print("\n" + "=" * 70)
        print("                    🧠 NEUROSENSE AI PLATFORM")
        print("              Live Behavioral Analysis Demonstration")
        print("=" * 70)
        print()
    
    def list_audio_devices(self):
        """Show available microphones"""
        print("🎤 Available Audio Devices:")
        print("-" * 70)
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only show input devices
                print(f"   [{i}] {device['name']}")
                print(f"       Channels: {device['max_input_channels']} | "
                      f"Sample Rate: {device['default_samplerate']} Hz")
        print("-" * 70)
        print()
    
    def record_demo_session(self, duration=10, scenario="normal"):
        """
        Record a demonstration session
        
        Args:
            duration: Recording length in seconds
            scenario: Behavioral scenario being demonstrated
        """
        self.show_header()
        
        print(f"📋 DEMO SESSION PARAMETERS")
        print(f"   Scenario: {scenario.upper()}")
        print(f"   Duration: {duration} seconds")
        print(f"   Sample Rate: {self.sample_rate} Hz (CD Quality)")
        print()
        
        # Recording guidance based on scenario
        self.show_scenario_guidance(scenario)
        
        input("Press ENTER when ready to begin recording...")
        print()
        
        # Countdown with visual feedback
        print("🎬 STARTING IN:")
        for i in range(3, 0, -1):
            print(f"        {i}...", end='', flush=True)
            time.sleep(1)
            print()
        
        print()
        print("🔴 RECORDING NOW - SPEAK CLEARLY")
        print("=" * 70)
        print()
        
        # Progress indicator
        print("Progress: [", end='', flush=True)
        
        # Record with progress updates
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='float64'
        )
        
        # Show progress bar
        for i in range(duration):
            time.sleep(1)
            print("█", end='', flush=True)
        
        sd.wait()
        print("] COMPLETE!")
        print()
        
        # Quick analysis
        peak = np.max(np.abs(recording))
        rms = np.sqrt(np.mean(recording**2))
        
        print("✅ RECORDING CAPTURED SUCCESSFULLY")
        print()
        print("📊 IMMEDIATE ANALYSIS:")
        print(f"   Peak Level: {peak:.3f} {'✅ Good' if peak > 0.1 else '⚠️ Low'}")
        print(f"   RMS Energy: {rms:.3f}")
        print(f"   Signal Quality: {'✅ Excellent' if peak > 0.1 else '⚠️ Check microphone'}")
        print()
        
        # Save with descriptive filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.recordings_folder}/demo_{scenario}_{timestamp}.wav"
        sf.write(filename, recording, self.sample_rate)
        
        print(f"💾 Saved: {filename}")
        print()
        
        return filename, recording
    
    def show_scenario_guidance(self, scenario):
        """Provide recording guidance based on scenario"""
        
        guidance = {
            "normal": [
                "Speak in your natural, conversational tone",
                "Read a paragraph or describe something calmly",
                "Maintain steady volume and pace"
            ],
            "stressed": [
                "Speak slightly faster than normal",
                "Raise your pitch slightly to simulate tension",
                "Add urgency to your voice (imagine running late)"
            ],
            "fatigued": [
                "Speak slowly and with low energy",
                "Lower your vocal energy significantly",
                "Add longer pauses, sound tired"
            ],
            "excited": [
                "Speak with high energy and enthusiasm",
                "Vary your pitch dramatically",
                "Animated, engaged tone (imagine good news!)"
            ],
            "baseline": [
                "This will be your baseline reference",
                "Speak naturally and comfortably",
                "This is what 'normal' sounds like for you"
            ]
        }
        
        print("🎭 SCENARIO GUIDANCE:")
        tips = guidance.get(scenario, guidance["normal"])
        for tip in tips:
            print(f"   • {tip}")
        print()
    
    def demo_multiple_scenarios(self):
        """Record multiple scenarios for comparison demo"""
        
        scenarios = [
            ("baseline", "Baseline (Normal State)", 8),
            ("stressed", "Stressed State", 8),
            ("fatigued", "Fatigued State", 8)
        ]
        
        self.show_header()
        
        print("🎬 MULTI-SCENARIO DEMONSTRATION")
        print()
        print("We'll record 3 different behavioral states to demonstrate")
        print("how NeuroSense AI detects changes in vocal patterns.")
        print()
        print("Scenarios to record:")
        for i, (key, name, duration) in enumerate(scenarios, 1):
            print(f"   {i}. {name} ({duration} seconds)")
        print()
        
        input("Press ENTER to begin the demonstration sequence...")
        
        recordings = []
        
        for scenario_key, scenario_name, duration in scenarios:
            print("\n" + "=" * 70)
            print(f"SCENARIO {len(recordings) + 1}: {scenario_name}")
            print("=" * 70)
            
            filename, recording = self.record_demo_session(
                duration=duration,
                scenario=scenario_key
            )
            
            recordings.append({
                'scenario': scenario_key,
                'name': scenario_name,
                'filename': filename,
                'recording': recording
            })
            
            if len(recordings) < len(scenarios):
                print("\n⏸️  Prepare for next scenario...")
                time.sleep(2)
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ ALL SCENARIOS RECORDED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("📁 Recorded Files:")
        for i, rec in enumerate(recordings, 1):
            print(f"   {i}. {rec['name']}")
            print(f"      {rec['filename']}")
        print()
        print("🔬 Ready for behavioral analysis comparison!")
        print()
        
        return recordings

def main():
    """Main demo interface"""
    recorder = DemoRecorder()
    
    recorder.show_header()
    
    print("SELECT DEMONSTRATION MODE:")
    print()
    print("   [1] Single Recording (Quick Demo)")
    print("   [2] Multi-Scenario Demo (Shows Pattern Detection)")
    print("   [3] List Audio Devices")
    print("   [4] Exit")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        print("\nSELECT SCENARIO:")
        print("   [1] Normal/Baseline")
        print("   [2] Stressed")
        print("   [3] Fatigued")
        print("   [4] Excited")
        print()
        scenario_choice = input("Enter scenario (1-4): ").strip()
        
        scenarios = {"1": "baseline", "2": "stressed", "3": "fatigued", "4": "excited"}
        scenario = scenarios.get(scenario_choice, "normal")
        
        duration = input("Duration in seconds (default 10): ").strip()
        duration = int(duration) if duration.isdigit() else 10
        
        recorder.record_demo_session(duration=duration, scenario=scenario)
        
    elif choice == "2":
        recorder.demo_multiple_scenarios()
        
    elif choice == "3":
        recorder.list_audio_devices()
        
    else:
        print("\n👋 Thank you for the demonstration!")
        return
    
    print("\n" + "=" * 70)
    print("Next step: Run 'audio_analyzer.py' to see AI analysis results!")
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()