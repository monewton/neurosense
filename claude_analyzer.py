"""
NeuroSense AI - Claude AI Integration Module
Real-time behavioral analysis using Claude AI
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ClaudeBehavioralAnalyzer:
    """
    Integration with Claude AI for behavioral pattern interpretation
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("Claude API key not found. Set CLAUDE_API_KEY environment variable.")
        
        self.session = None
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))
    
    async def initialize(self):
        """Initialize the API session"""
        self.session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        print("✅ Claude AI connection initialized")
    
    async def analyze_behavioral_data(self, audio_features: Dict) -> Dict:
        """
        Send behavioral data to Claude for AI analysis
        
        Args:
            audio_features: Dictionary containing extracted audio features
            
        Returns:
            Dictionary with Claude analysis and interpretation
        """
        
        if not self.session:
            await self.initialize()
        
        # Create the prompt for Claude
        prompt = self._create_analysis_prompt(audio_features)
        
        print("\n🤖 Sending data to Claude AI...")
        print("📊 Analyzing behavioral patterns...")
        
        try:
            # Make API request to Claude
            async with self.session.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    claude_text = result["content"][0]["text"]
                    if result.get("stop_reason") == "max_tokens":
                        print(
                            f"⚠️ Claude hit max_tokens ({self.max_tokens}); "
                            "narrative may be truncated. Raise CLAUDE_MAX_TOKENS and re-run."
                        )
                    
                    # Parse Claude's response
                    analysis = self._parse_claude_response(claude_text, audio_features)
                    
                    print("✅ Analysis complete!")
                    return analysis
                    
                else:
                    error_text = await response.text()
                    return {
                        "error": f"API Error: {response.status}",
                        "details": error_text
                    }
                    
        except Exception as e:
            return {
                "error": f"Connection error: {str(e)}",
                "details": "Please check your internet connection and API key"
            }
    
    def _create_analysis_prompt(self, features: Dict) -> str:
        """Create a detailed prompt for Claude behavioral analysis"""

        def g(key, default=0):
            return features.get(key, default)

        prompt = f"""You are analyzing behavioral data from the NeuroSense AI platform, which monitors subjects for neurological assessment and TBI research.

BEHAVIORAL DATA ANALYSIS REQUEST:

Composite scores:
- Overall Behavioral Score: {g('behavioral_score')}/100
- Stress Level: {g('stress_level')}/100
- Vocal Stability Index: {g('vocal_stability'):.3f}

Inferred emotional state (acoustic-proxy affective model):
- Primary: {g('primary_emotion', 'n/a')} at level {g('emotion_level', 'n/a')}/5 [{g('emotion_traffic_light', 'n/a')}]
- Activations: {g('emotional_activations', {})}
- Blend: {g('emotion_blend', None)}
- Within-clip volatility: {g('emotion_volatility', 0):.3f}
- Emotion confidence: {g('emotion_confidence', 0):.1f}/100 (falls when volatility/mixing is high)
- Plain-language: {g('emotion_interpretation', 'n/a')}

Acoustic feature families (researcher integration set):
1) Pitch — F0 mean: {g('f0_mean', g('pitch_mean')):.1f} Hz; variability (CV): {g('pitch_variation'):.3f}; range: {g('pitch_range'):.1f} Hz
2) Speech rate — {g('speaking_rate'):.2f} syl/sec; ~{g('speaking_rate_wpm'):.1f} WPM (acoustic proxy); onset latency: {g('response_latency_sec'):.3f}s
3) Intensity — RMS: {g('rms_energy'):.4f}; peak-to-average: {g('peak_to_average_ratio', g('dynamic_range')):.2f}x
4) Voice quality — tension: {g('tension'):.3f}; roughness: {g('roughness'):.4f}; jitter: {g('jitter'):.4f}; shimmer: {g('shimmer'):.4f}
5) Pauses/disfluencies — pause ratio: {g('pause_ratio'):.1%}; mean pause: {g('mean_pause_duration_sec'):.3f}s; cutoffs/min: {g('cutoff_rate_per_min'):.2f}; filler proxy/min: {g('filler_proxy_rate_per_min'):.2f}
6) Prosody — contour slope: {g('prosody_contour_slope'):.2f} Hz/s; rhythm regularity: {g('prosody_rhythm_regularity'):.3f}; emphasis: {g('prosody_emphasis'):.2f}
7) Articulation — clarity: {g('articulation_clarity'):.3f}; slur index: {g('slur_index'):.3f}; over-articulation: {g('over_articulation_index'):.3f}
{self._pause_capture_note(features)}
CONTEXT:
Acoustic markers are proxies for underlying affective/physiological state (SOCOM framing). The emotional-state layer translates those proxies into stress/sadness/anger/neutral activations, level, traffic light, volatility, and confidence — so clinicians can ask “what does this mean?”, “how stable is it?”, and later “did treatment change it?” versus baseline. WPM/filler lexical counts are optional ASR enrichments; they are not required for the affective model.

ANALYSIS REQUEST:
Provide a comprehensive behavioral assessment including:

1. OVERALL BEHAVIORAL / EMOTIONAL STATUS (one sentence)

2. INTERPRET the emotional activations and whether the state looks stable or volatile

3. KEY ACOUSTIC DRIVERS across the seven families

4. CLINICAL / OPERATIONAL MEANING:
   - What this may imply for stress, mood, or engagement
   - What would indicate change after therapy / redeployment (compare later sessions)

5. MONITORING RECOMMENDATIONS (which markers + volatility/confidence to track)

6. CONFIDENCE — reconcile with the numeric emotion confidence; note limits

Be specific. Treat AI output as adjunctive, not a diagnosis.
"""
        return prompt

    @staticmethod
    def _pause_capture_note(features: Dict) -> str:
        if not features.get("pause_collapse_applied"):
            return ""
        n = features.get("n_gaps_collapsed", 0)
        removed = features.get("removed_sec", 0)
        limit = features.get("max_pause_sec_used", 2.0)
        orig = features.get("original_duration_sec", 0)
        kept = features.get("collapsed_duration_sec", 0)
        return (
            f"\nCapture note — patient-only: interviewer was off-mic. "
            f"Collapsed {n} silences longer than {limit:.1f}s "
            f"({removed:.1f}s removed; {orig:.1f}s -> {kept:.1f}s). "
            "Pause/rate/sadness metrics are from the speaker's turns, not turn-taking gaps.\n"
        )

    def _parse_claude_response(self, claude_text: str, features: Dict) -> Dict:
        """Parse and structure Claude's response"""

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "raw_analysis": claude_text,
            "behavioral_score": features.get("behavioral_score", 0),
            "stress_level": features.get("stress_level", 0),
            "features_analyzed": {
                "pitch": {
                    "f0_mean": features.get("f0_mean", features.get("pitch_mean", 0)),
                    "pitch_variation": features.get("pitch_variation", 0),
                },
                "speech_rate": {
                    "speaking_rate": features.get("speaking_rate", 0),
                    "speaking_rate_wpm": features.get("speaking_rate_wpm", 0),
                    "response_latency_sec": features.get("response_latency_sec", 0),
                },
                "intensity": {
                    "rms_energy": features.get("rms_energy", 0),
                    "peak_to_average_ratio": features.get(
                        "peak_to_average_ratio", features.get("dynamic_range", 0)
                    ),
                },
                "voice_quality": {
                    "tension": features.get("tension", 0),
                    "roughness": features.get("roughness", 0),
                    "jitter": features.get("jitter", 0),
                    "shimmer": features.get("shimmer", 0),
                },
                "pauses": {
                    "pause_ratio": features.get("pause_ratio", 0),
                    "cutoff_rate_per_min": features.get("cutoff_rate_per_min", 0),
                    "filler_proxy_rate_per_min": features.get("filler_proxy_rate_per_min", 0),
                },
                "prosody": {
                    "contour_slope": features.get("prosody_contour_slope", 0),
                    "rhythm_regularity": features.get("prosody_rhythm_regularity", 0),
                    "emphasis": features.get("prosody_emphasis", 0),
                },
                "articulation": {
                    "clarity": features.get("articulation_clarity", 0),
                    "slur_index": features.get("slur_index", 0),
                    "over_articulation_index": features.get("over_articulation_index", 0),
                },
                "vocal_stability": features.get("vocal_stability", 0),
            },
            "ai_model": self.model,
        }
        
        # Try to extract structured information
        # Look for confidence level
        if "confidence" in claude_text.lower():
            if "high" in claude_text.lower():
                analysis["confidence"] = "High"
            elif "medium" in claude_text.lower():
                analysis["confidence"] = "Medium"
            elif "low" in claude_text.lower():
                analysis["confidence"] = "Low"
            else:
                analysis["confidence"] = "Medium"
        else:
            analysis["confidence"] = "Medium"
        
        # Determine overall status from Claude's analysis
        if any(word in claude_text.lower() for word in ["concerning", "abnormal", "warning", "decline"]):
            analysis["status"] = "Needs Attention"
        elif any(word in claude_text.lower() for word in ["excellent", "healthy", "normal", "good"]):
            analysis["status"] = "Good"
        else:
            analysis["status"] = "Fair"
        
        return analysis
    
    async def close(self):
        """Close the API session"""
        if self.session:
            await self.session.close()
            print("🔌 Claude AI connection closed")

async def analyze_recording_with_claude(audio_features: Dict):
    """
    Convenience function to analyze audio features with Claude
    
    Args:
        audio_features: Dictionary of extracted audio features
        
    Returns:
        Claude's behavioral analysis
    """
    
    analyzer = ClaudeBehavioralAnalyzer()
    
    try:
        await analyzer.initialize()
        analysis = await analyzer.analyze_behavioral_data(audio_features)
        return analysis
    finally:
        await analyzer.close()

# Test function
async def test_claude_integration():
    """Test the Claude integration with sample data"""
    
    print("=" * 70)
    print("NEUROSENSE AI - CLAUDE INTEGRATION TEST")
    print("=" * 70)
    print()
    
    # Sample behavioral features (simulate what audio_analyzer.py extracts)
    sample_features = {
        "rms_energy": 0.0234,
        "peak_amplitude": 0.1456,
        "dominant_frequency": 185.3,
        "speech_ratio": 0.62,
        "vocal_stability": 0.78,
        "behavioral_score": 72
    }
    
    print("📊 Sample Behavioral Features:")
    for key, value in sample_features.items():
        print(f"   {key}: {value}")
    print()
    
    # Analyze with Claude
    analysis = await analyze_recording_with_claude(sample_features)
    
    # Display results
    if "error" in analysis:
        print("❌ ERROR:")
        print(f"   {analysis['error']}")
        if "details" in analysis:
            print(f"   {analysis['details']}")
    else:
        print("\n" + "=" * 70)
        print("🤖 CLAUDE AI BEHAVIORAL ANALYSIS")
        print("=" * 70)
        print()
        print(analysis["raw_analysis"])
        print()
        print("=" * 70)
        print("📋 ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Status: {analysis['status']}")
        print(f"Confidence: {analysis['confidence']}")
        print(f"Analyzed at: {analysis['timestamp']}")
        print(f"AI Model: {analysis['ai_model']}")
        print()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_claude_integration())