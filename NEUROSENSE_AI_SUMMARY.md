# NeuroSense AI - Application Summary

## Overview

NeuroSense AI is a sophisticated behavioral analysis platform designed for neurological assessment and Traumatic Brain Injury (TBI) research. The application uses advanced audio signal processing and artificial intelligence to analyze vocal patterns and extract behavioral indicators from audio recordings. While designed for monitoring animal subjects in clinical research settings, the current implementation uses human voice data to demonstrate and validate the behavioral pattern detection capabilities.

## Core Purpose

The platform serves as a non-invasive monitoring system that can:
- Capture vocal and behavioral data through audio recordings
- Extract quantitative features that correlate with behavioral states
- Use AI (Claude) to interpret patterns and provide clinical insights
- Detect stress, fatigue, excitement, and other behavioral states
- Generate comprehensive reports for research and clinical use

## Technical Architecture

### 1. Audio Recording Module (`simple_recorder.py`, `demo_recorder.py`)

**Functionality:**
- Records audio at CD-quality (44.1 kHz sample rate)
- Supports configurable recording durations
- Creates timestamped WAV files in a dedicated recordings folder
- Provides real-time feedback on recording quality
- Supports multiple behavioral scenarios (baseline, stressed, fatigued, excited)

**Key Features:**
- Professional demo interface for client presentations
- Multi-scenario recording capability for comparative analysis
- Audio device detection and selection
- Progress indicators and visual feedback during recording
- Automatic file naming with scenario tags and timestamps

### 2. Feature Extraction Engine (`audio_analyzer.py`, `enhanced_features.py`)

**Core Analysis Capabilities:**

#### Energy Analysis
- **RMS Energy**: Root mean square energy measurement indicating overall vocal activity level
- **Peak Amplitude**: Maximum signal strength, useful for detecting intensity variations
- **Dynamic Range**: Ratio of peak to RMS, indicating vocal variability

#### Frequency Analysis
- **Dominant Frequency**: Primary vocal frequency in the human vocal range (80-1000 Hz)
- **Frequency Spread**: Standard deviation of frequencies, indicating vocal stability
- **High Frequency Ratio**: Energy in higher frequencies (500-4000 Hz), an indicator of vocal tension

#### Temporal Pattern Analysis
- **Speech/Voice Ratio**: Percentage of time with active vocalization
- **Energy Variance**: Variation in frame-by-frame energy levels
- **Voice Activity Detection**: Identifies periods of speech vs. silence using adaptive thresholds

#### Advanced Pitch Analysis (Enhanced Features)
- **Pitch Mean**: Average fundamental frequency over the recording
- **Pitch Variation**: Coefficient of variation in pitch (key stress indicator)
- **Pitch Range**: Difference between highest and lowest detected pitches
- Uses autocorrelation method for accurate pitch tracking

#### Speaking Rate Analysis
- **Syllable Rate**: Estimated syllables per second
- Uses energy envelope analysis to detect speech bursts
- Helps identify rapid speech patterns associated with stress or excitement

#### Stress-Specific Indicators
- **Jitter**: Short-term variation in vocal energy (voice instability measure)
- **Spectral Flux**: Rate of spectral change over time (arousal indicator)
- **Composite Stress Score**: Multi-factor stress level calculation (0-100 scale)

### 3. Behavioral Scoring System

**Behavioral Score Calculation (0-100 scale):**
- Base score: 50 points
- Energy level contributions: +5 to +15 points based on RMS energy
- Speech activity contributions: +10 to +15 points based on engagement
- Pitch stability bonuses: +5 to +10 points for stable vocalization
- Speaking rate bonuses: +10 points for normal range (2-4 syllables/sec)
- Stress penalties: Up to -20 points for high stress indicators

**Stress Level Calculation (0-100 scale):**
- Pitch variation analysis: Up to +25 points
- Speaking rate analysis: Up to +25 points
- High frequency content: Up to +20 points
- Energy variance: Up to +15 points
- Jitter measurement: Up to +15 points

### 4. Claude AI Integration (`claude_analyzer.py`, `claude_demo.py`)

**AI Analysis Pipeline:**

The system integrates with Anthropic's Claude AI (Claude Sonnet 4) to provide intelligent interpretation of extracted features. The integration includes:

**Data Transmission:**
- Sends structured feature data to Claude API
- Includes behavioral scores, energy metrics, frequency patterns, and temporal indicators
- Provides clinical context for TBI research applications

**AI Interpretation Request:**
Claude receives a comprehensive prompt requesting:
1. **Overall Behavioral Status**: One-sentence summary assessment
2. **Key Behavioral Indicators**: Analysis of energy levels, frequency patterns, and vocal stability
3. **Clinical Interpretation**: What patterns suggest for TBI research subjects
4. **Pattern Assessment**: Evaluation of normalcy, stress indicators, and activity appropriateness
5. **Monitoring Recommendations**: Suggested changes to monitoring frequency and metrics to watch
6. **Confidence Level**: Assessment confidence (High/Medium/Low) and data needs

**Response Processing:**
- Parses Claude's natural language analysis
- Extracts structured information (status, confidence level)
- Identifies concerning vs. positive indicators
- Generates timestamped analysis reports

### 5. Visualization and Reporting (`audio_analyzer.py`)

**Visual Analysis Outputs:**
- **Waveform Plot**: Time-domain visualization of the audio signal
- **Frequency Spectrum**: Frequency domain analysis showing vocal range characteristics
- **Voice Activity Detection Plot**: Temporal visualization of speech vs. silence periods with threshold indicators

**Report Generation:**
- Saves high-resolution PNG visualizations (150 DPI)
- Includes timestamped filenames matching audio recordings
- Provides comprehensive feature summaries in console output

## Workflow and User Experience

### Standard Workflow

1. **Recording Phase**
   - User selects behavioral scenario (baseline, stressed, fatigued, excited)
   - System records audio for specified duration (typically 8-10 seconds)
   - Real-time feedback on recording quality
   - Automatic file saving with descriptive naming

2. **Feature Extraction Phase**
   - Audio file is automatically analyzed
   - Multiple feature categories are extracted simultaneously
   - Behavioral and stress scores are calculated
   - Results are displayed in organized format

3. **AI Analysis Phase** (Optional)
   - Extracted features are sent to Claude AI
   - AI provides clinical interpretation
   - Structured analysis report is generated
   - Confidence levels and recommendations are provided

4. **Visualization Phase**
   - Multi-panel plots are generated
   - Visualizations are saved for documentation
   - Comparative analysis can be performed across scenarios

### Demo and Presentation Features

The application includes professional demonstration tools:
- **Multi-Scenario Recording**: Record baseline, stressed, and fatigued states for comparison
- **Scenario Guidance**: Instructions for simulating different behavioral states
- **Progress Indicators**: Visual feedback during recording and processing
- **Professional Formatting**: Clean console output suitable for client presentations

## Technical Specifications

### Audio Processing
- **Sample Rate**: 44,100 Hz (CD quality)
- **Channels**: Mono (single channel)
- **Format**: WAV files (uncompressed)
- **Frame Analysis**: 25ms frames with 10ms hop length for temporal analysis
- **Frequency Range**: Focus on 80-1000 Hz for vocal analysis, extended to 4000 Hz for tension detection

### Dependencies
- **sounddevice**: Real-time audio recording
- **soundfile**: Audio file I/O
- **numpy**: Numerical computations and signal processing
- **scipy**: Advanced signal processing (FFT, autocorrelation)
- **matplotlib**: Visualization and plotting
- **aiohttp**: Asynchronous HTTP for Claude API integration
- **python-dotenv**: Environment variable management for API keys

### File Organization
- **Recordings Folder**: Stores all audio recordings with timestamped filenames
- **Analysis Outputs**: PNG visualizations saved alongside recordings
- **Naming Convention**: `[type]_[scenario]_[timestamp].wav` for recordings, `analysis_[recording_name].png` for visualizations

## Clinical and Research Applications

### Primary Use Cases

1. **TBI Research Monitoring**
   - Track behavioral changes in research subjects over time
   - Detect early indicators of neurological changes
   - Monitor recovery progress

2. **Behavioral State Assessment**
   - Identify stress levels and arousal states
   - Detect fatigue and reduced activity
   - Monitor engagement and responsiveness

3. **Longitudinal Studies**
   - Establish baseline behavioral profiles
   - Track changes over time
   - Compare pre- and post-intervention states

4. **Clinical Decision Support**
   - Provide objective behavioral metrics
   - Generate alerts for concerning patterns
   - Support treatment planning

## Key Innovations

1. **Multi-Modal Feature Extraction**: Combines energy, frequency, temporal, and pitch analysis for comprehensive behavioral assessment

2. **Stress-Specific Indicators**: Advanced metrics like jitter, spectral flux, and pitch variation specifically designed to detect stress and arousal

3. **AI-Enhanced Interpretation**: Uses Claude AI to provide clinical context and recommendations, not just raw metrics

4. **Non-Invasive Monitoring**: Audio-based approach eliminates need for physical sensors or invasive procedures

5. **Real-Time Capability**: Designed for both batch analysis and potential real-time monitoring applications

## Limitations and Future Enhancements

**Current Limitations:**
- Uses human voice for demonstration (designed for animal subjects in production)
- Requires manual recording initiation
- Analysis is post-recording (not fully real-time)
- Requires Claude API key for AI features

**Potential Enhancements:**
- Real-time continuous monitoring
- Machine learning models trained on clinical data
- Integration with other sensor modalities
- Automated alerting system
- Database for longitudinal tracking
- Web-based dashboard interface

## Conclusion

NeuroSense AI represents a sophisticated approach to behavioral monitoring that combines signal processing expertise with modern AI capabilities. The platform provides researchers and clinicians with objective, quantitative measures of behavioral states while offering intelligent interpretation through AI integration. The modular architecture allows for easy extension and customization for specific research needs, making it a valuable tool for neurological assessment and TBI research applications.
