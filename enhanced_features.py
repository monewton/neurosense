"""
NeuroSense AI - Enhanced Feature Extraction with Stress Detection

Core analysis engine for the NeuroSense pipeline. Every entry point
(audio_analyzer, claude_demo, future API/wearable integrations) calls
this module to turn a voice sample into quantitative behavioral metrics.

Researcher acoustic contract (integration objective):
  - Pitch: fundamental frequency (F0), variability
  - Speech rate: words-per-minute proxy, response/onset latency
  - Intensity: RMS energy, peak-to-average ratio
  - Voice quality: tension, roughness, jitter, shimmer
  - Pauses/disfluencies: pause ratio, acoustic filler proxy, cutoff events
  - Prosody: contour, rhythm, emphasis
  - Articulation: clarity, slurring, over-articulation proxies

Also emits composite stress_level / behavioral_score / vocal_stability for
existing dashboards, Claude interpretation, and session_history.

Note: true lexical fillers and word-accurate WPM require ASR/transcript.
This module provides acoustic proxies so analysis works on audio-only input.
"""

from __future__ import annotations

import numpy as np


# Approximate syllables per English word — used only as an acoustic WPM proxy.
_SYLLABLES_PER_WORD = 1.5


class EnhancedFeatureExtractor:
    """
    Converts mono audio (numpy float array) into a behavioral feature dictionary.

    Designed for check-in and telephony clips at 8–44.1 kHz.
    Thresholds are tuned for human voice; wearable deployments may
    recalibrate for wrist-mounted mics or alternate sample rates.
    """

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def extract_all_features(self, audio_data):
        """
        Run the full feature pipeline and return a single metrics dict.

        Pipeline order matters: raw acoustic families first, then derived scores.
        stress_level is computed before behavioral_score because the latter
        penalizes high stress.
        """
        audio_data = np.asarray(audio_data, dtype=float)
        features = {}

        # Intensity — RMS, peak, peak-to-average
        features.update(self._extract_energy_features(audio_data))

        # Spectral content in the human vocal range
        features.update(self._extract_frequency_features(audio_data))

        # Voice activity / temporal energy
        features.update(self._extract_temporal_features(audio_data))

        # Pitch (F0) + contour inputs
        pitch_bundle = self._extract_pitch_features(audio_data)
        features.update(pitch_bundle)

        # Speech rate (syllables/sec, WPM proxy) + onset latency
        rate_bundle = self._extract_rate_features(audio_data)
        features.update(rate_bundle)

        # Voice quality — jitter, shimmer, tension, roughness
        features.update(self._extract_voice_quality(audio_data, pitch_bundle.get("_pitch_track")))

        # Pauses / disfluency acoustic proxies
        features.update(self._extract_pause_features(audio_data))

        # Prosody — contour, rhythm, emphasis
        features.update(
            self._extract_prosody_features(
                audio_data,
                pitch_bundle.get("_pitch_track"),
                rate_bundle.get("_peak_times"),
            )
        )

        # Articulation proxies — clarity / slur / over-articulation
        features.update(self._extract_articulation_features(audio_data))

        # Drop internal helper keys from the public contract
        features.pop("_pitch_track", None)
        features.pop("_peak_times", None)

        # Composite scores (existing product outputs)
        features["stress_level"] = self._calculate_stress_level(features)
        features["behavioral_score"] = self._calculate_enhanced_score(features)

        pitch_var = features.get("pitch_variation", 0)
        features["vocal_stability"] = float(1.0 / (1.0 + pitch_var)) if pitch_var else 1.0

        return features

    def _extract_energy_features(self, audio_data):
        """Intensity: RMS energy, peak amplitude, peak-to-average ratio."""

        rms_energy = np.sqrt(np.mean(audio_data**2)) if len(audio_data) else 0.0
        peak_amplitude = float(np.max(np.abs(audio_data))) if len(audio_data) else 0.0

        # peak-to-average == dynamic_range (kept under both names for researchers)
        if rms_energy > 0:
            peak_to_average = peak_amplitude / rms_energy
        else:
            peak_to_average = 0.0

        return {
            "rms_energy": float(rms_energy),
            "peak_amplitude": float(peak_amplitude),
            "dynamic_range": float(peak_to_average),
            "peak_to_average_ratio": float(peak_to_average),
        }

    def _extract_frequency_features(self, audio_data):
        """
        FFT-based vocal analysis.

        dominant_frequency: primary pitch band in the clip
        frequency_std: spread of energy across frequencies (instability proxy)
        high_frequency_ratio: energy above 500 Hz — rises with vocal tension
        """
        fft_data = np.fft.fft(audio_data)
        frequencies = np.fft.fftfreq(len(fft_data), 1 / self.sample_rate)
        magnitudes = np.abs(fft_data)

        # Human speech fundamentals typically fall between 80-1000 Hz
        vocal_mask = (frequencies >= 80) & (frequencies <= 1000)
        vocal_freqs = frequencies[vocal_mask]
        vocal_mags = magnitudes[vocal_mask]

        if len(vocal_mags) > 0 and np.max(vocal_mags) > 0:
            dominant_idx = np.argmax(vocal_mags)
            dominant_freq = abs(vocal_freqs[dominant_idx])

            # Magnitude-weighted spread — wider spread suggests less stable voicing
            weighted_freqs = vocal_freqs * vocal_mags
            mean_freq = np.sum(weighted_freqs) / np.sum(vocal_mags)
            freq_variance = np.sum(vocal_mags * (vocal_freqs - mean_freq) ** 2) / np.sum(vocal_mags)
            freq_std = np.sqrt(freq_variance)

            # Tension / strain often adds energy in higher harmonics (500-4000 Hz)
            high_freq_mask = (frequencies >= 500) & (frequencies <= 4000)
            high_freq_energy = np.sum(magnitudes[high_freq_mask])
            total_energy = np.sum(magnitudes[vocal_mask])
            high_freq_ratio = high_freq_energy / total_energy if total_energy > 0 else 0

        else:
            dominant_freq = 0
            freq_std = 0
            high_freq_ratio = 0

        return {
            "dominant_frequency": float(dominant_freq),
            "frequency_std": float(freq_std),
            "high_frequency_ratio": float(high_freq_ratio),
        }

    def _extract_temporal_features(self, audio_data):
        """
        Frame-based voice activity detection (VAD) and energy variability.

        speech_ratio: fraction of 25 ms frames above an adaptive energy threshold
        energy_variance: how erratically loudness changes — stress / agitation signal
        """
        frame_length = int(0.025 * self.sample_rate)  # 25 ms — standard speech frame
        hop_length = int(0.010 * self.sample_rate)  # 10 ms hop for time resolution

        frame_energies = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]
            energy = np.sum(frame**2)
            frame_energies.append(energy)

        frame_energies = np.array(frame_energies)

        if len(frame_energies) > 0:
            # Frames above half the mean energy count as "active voice"
            threshold = np.mean(frame_energies) * 0.5
            speech_frames = frame_energies > threshold
            speech_ratio = np.sum(speech_frames) / len(speech_frames)

            energy_variance = np.var(frame_energies)
            energy_std = np.std(frame_energies)
        else:
            speech_ratio = 0
            energy_variance = 0
            energy_std = 0

        return {
            "speech_ratio": float(speech_ratio),
            "energy_variance": float(energy_variance),
            "energy_std": float(energy_std),
        }

    def _extract_pitch_features(self, audio_data):
        """
        Pitch / F0 via autocorrelation.

        Public fields: pitch_mean (F0), pitch_std, pitch_range, pitch_variation.
        Also returns internal _pitch_track [(time_sec, f0), ...] for prosody.
        """
        frame_length = int(0.040 * self.sample_rate)
        hop_length = int(0.010 * self.sample_rate)

        pitches = []
        pitch_track = []

        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]

            if np.max(np.abs(frame)) < 0.01:
                continue

            autocorr = np.correlate(frame, frame, mode="full")
            autocorr = autocorr[len(autocorr) // 2 :]

            min_period = int(self.sample_rate / 400)
            max_period = int(self.sample_rate / 80)

            if max_period < len(autocorr):
                autocorr_segment = autocorr[min_period:max_period]
                if len(autocorr_segment) > 0:
                    peak_idx = np.argmax(autocorr_segment) + min_period
                    pitch = self.sample_rate / peak_idx

                    if 80 <= pitch <= 400:
                        t_sec = i / self.sample_rate
                        pitches.append(pitch)
                        pitch_track.append((t_sec, float(pitch)))

        if len(pitches) > 2:
            pitch_mean = float(np.mean(pitches))
            pitch_std = float(np.std(pitches))
            pitch_range = float(np.max(pitches) - np.min(pitches))
            pitch_cv = pitch_std / pitch_mean if pitch_mean > 0 else 0.0
        else:
            pitch_mean = 0.0
            pitch_std = 0.0
            pitch_range = 0.0
            pitch_cv = 0.0

        return {
            "pitch_mean": pitch_mean,
            "f0_mean": pitch_mean,
            "pitch_std": pitch_std,
            "pitch_range": pitch_range,
            "pitch_variation": float(pitch_cv),
            "pitch_variability": float(pitch_cv),
            "_pitch_track": pitch_track,
        }

    def _extract_rate_features(self, audio_data):
        """
        Speech rate from energy-envelope peaks + onset (response) latency.

        speaking_rate: syllables/sec proxy
        speaking_rate_wpm: acoustic words-per-minute proxy (not ASR word count)
        response_latency_sec: time to first speech-energy onset in the clip
        """
        frame_length = int(0.020 * self.sample_rate)
        hop_length = int(0.010 * self.sample_rate)

        envelope = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]
            envelope.append(float(np.sum(np.abs(frame))))

        envelope = np.array(envelope)
        peak_times = []
        syllable_rate = 0.0
        response_latency = 0.0

        if len(envelope) > 0:
            window_size = 5
            if len(envelope) >= window_size:
                envelope_smooth = np.convolve(
                    envelope, np.ones(window_size) / window_size, mode="same"
                )
            else:
                envelope_smooth = envelope

            mean_env = float(np.mean(envelope_smooth))
            threshold = mean_env * 1.5
            onset_threshold = mean_env * 0.5

            # Response / onset latency: first frame above speech energy
            for i, val in enumerate(envelope_smooth):
                if val > onset_threshold:
                    response_latency = i * hop_length / self.sample_rate
                    break
            else:
                response_latency = len(audio_data) / self.sample_rate if len(audio_data) else 0.0

            for i in range(1, len(envelope_smooth) - 1):
                if (
                    envelope_smooth[i] > envelope_smooth[i - 1]
                    and envelope_smooth[i] > envelope_smooth[i + 1]
                    and envelope_smooth[i] > threshold
                ):
                    peak_times.append(i * hop_length / self.sample_rate)

            duration = len(audio_data) / self.sample_rate
            syllable_rate = len(peak_times) / duration if duration > 0 else 0.0

        # Acoustic WPM proxy (syllables/sec → words/min)
        speaking_rate_wpm = (syllable_rate * 60.0) / _SYLLABLES_PER_WORD

        return {
            "speaking_rate": float(syllable_rate),
            "speaking_rate_wpm": float(speaking_rate_wpm),
            "response_latency_sec": float(response_latency),
            "_peak_times": peak_times,
        }

    def _extract_voice_quality(self, audio_data, pitch_track):
        """
        Voice quality: jitter, shimmer, tension, roughness (+ spectral flux).

        jitter: short-term amplitude period instability (energy CV proxy)
        shimmer: cycle-to-cycle amplitude perturbation using F0 periods when available
        tension: high-frequency energy ratio in voiced speech
        roughness: spectral flatness / irregularity proxy (higher = rougher)
        """
        # --- Jitter (legacy energy-segment CV) ---
        if len(audio_data) > 100:
            segment_length = max(1, int(0.01 * self.sample_rate))
            segments = []
            for i in range(0, len(audio_data) - segment_length, segment_length):
                segment = audio_data[i : i + segment_length]
                segments.append(float(np.sqrt(np.mean(segment**2))))
            jitter = (
                float(np.std(segments) / (np.mean(segments) + 1e-4))
                if len(segments) > 1
                else 0.0
            )
        else:
            jitter = 0.0

        # --- Shimmer from successive voiced F0 periods ---
        shimmer = 0.0
        if pitch_track and len(pitch_track) > 3:
            amps = []
            for t_sec, f0 in pitch_track:
                period = int(self.sample_rate / f0) if f0 > 0 else 0
                center = int(t_sec * self.sample_rate)
                if period < 4 or center + period >= len(audio_data) or center < 0:
                    continue
                cycle = audio_data[center : center + period]
                amps.append(float(np.max(np.abs(cycle))))
            if len(amps) > 2:
                diffs = [abs(amps[i] - amps[i - 1]) for i in range(1, len(amps))]
                shimmer = float(np.mean(diffs) / (np.mean(amps) + 1e-6))

        # --- Spectral flux (arousal / change rate) ---
        frame_length = int(0.040 * self.sample_rate)
        hop_length = int(0.020 * self.sample_rate)
        spectral_flux_values = []
        flatness_values = []
        prev_spectrum = None

        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]
            if np.max(np.abs(frame)) < 0.01:
                prev_spectrum = None
                continue
            spectrum = np.abs(np.fft.fft(frame))[: frame_length // 2]
            spectrum = np.maximum(spectrum, 1e-12)

            if prev_spectrum is not None and len(prev_spectrum) == len(spectrum):
                spectral_flux_values.append(float(np.sum((spectrum - prev_spectrum) ** 2)))

            # Spectral flatness: geometric_mean / arithmetic_mean (noise-like → rough)
            log_mean = float(np.mean(np.log(spectrum)))
            arith_mean = float(np.mean(spectrum))
            flatness_values.append(float(np.exp(log_mean) / (arith_mean + 1e-12)))
            prev_spectrum = spectrum

        spectral_flux = float(np.mean(spectral_flux_values)) if spectral_flux_values else 0.0
        roughness = float(np.mean(flatness_values)) if flatness_values else 0.0

        # --- Tension from high-frequency ratio on full clip ---
        fft_data = np.fft.fft(audio_data) if len(audio_data) else np.array([0.0])
        frequencies = np.fft.fftfreq(len(fft_data), 1 / self.sample_rate) if len(audio_data) else np.array([0.0])
        magnitudes = np.abs(fft_data)
        vocal_mask = (frequencies >= 80) & (frequencies <= 1000)
        high_mask = (frequencies >= 500) & (frequencies <= 4000)
        vocal_e = float(np.sum(magnitudes[vocal_mask])) if np.any(vocal_mask) else 0.0
        high_e = float(np.sum(magnitudes[high_mask])) if np.any(high_mask) else 0.0
        tension = high_e / vocal_e if vocal_e > 0 else 0.0

        return {
            "jitter": float(jitter),
            "shimmer": float(shimmer),
            "tension": float(tension),
            "roughness": float(roughness),
            "spectral_flux": float(spectral_flux),
            # Keep prior stress-indicator naming used elsewhere
            "voice_tension": float(tension),
        }

    def _extract_pause_features(self, audio_data):
        """
        Pauses / disfluencies (acoustic).

        pause_ratio, pause_count, mean/max pause duration
        cutoff_rate: abrupt speech→silence collapses per minute
        filler_proxy_rate: brief mid-energy voiced islands per minute (not lexical ASR fillers)
        """
        frame_length = int(0.025 * self.sample_rate)
        hop_length = int(0.010 * self.sample_rate)
        hop_sec = hop_length / self.sample_rate
        duration_sec = len(audio_data) / self.sample_rate if len(audio_data) else 0.0

        frame_energies = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame_energies.append(float(np.sum(audio_data[i : i + frame_length] ** 2)))
        frame_energies = np.array(frame_energies)

        if len(frame_energies) == 0:
            return {
                "pause_ratio": 1.0,
                "pause_count": 0,
                "mean_pause_duration_sec": 0.0,
                "max_pause_duration_sec": 0.0,
                "cutoff_rate_per_min": 0.0,
                "filler_proxy_rate_per_min": 0.0,
            }

        threshold = float(np.mean(frame_energies) * 0.5)
        speech = frame_energies > threshold

        # Pause runs (contiguous non-speech)
        pause_lengths = []
        run = 0
        for is_speech in speech:
            if not is_speech:
                run += 1
            elif run > 0:
                pause_lengths.append(run * hop_sec)
                run = 0
        if run > 0:
            pause_lengths.append(run * hop_sec)

        # Ignore micro-gaps < 50 ms as measurement noise
        pauses = [p for p in pause_lengths if p >= 0.05]
        pause_ratio = float(1.0 - (np.sum(speech) / len(speech)))
        mean_pause = float(np.mean(pauses)) if pauses else 0.0
        max_pause = float(np.max(pauses)) if pauses else 0.0

        # Cutoffs: high-energy speech frame followed quickly by silence
        cutoffs = 0
        for i in range(1, len(speech) - 1):
            if speech[i - 1] and not speech[i]:
                if frame_energies[i - 1] > threshold * 2.0:
                    cutoffs += 1

        # Filler proxy: short speech islands 80–350 ms
        filler_islands = 0
        run = 0
        for is_speech in speech:
            if is_speech:
                run += 1
            elif run > 0:
                dur = run * hop_sec
                if 0.08 <= dur <= 0.35:
                    filler_islands += 1
                run = 0
        if run > 0:
            dur = run * hop_sec
            if 0.08 <= dur <= 0.35:
                filler_islands += 1

        minutes = max(duration_sec / 60.0, 1e-6)
        return {
            "pause_ratio": pause_ratio,
            "pause_count": int(len(pauses)),
            "mean_pause_duration_sec": mean_pause,
            "max_pause_duration_sec": max_pause,
            "cutoff_rate_per_min": float(cutoffs / minutes),
            "filler_proxy_rate_per_min": float(filler_islands / minutes),
        }

    def _extract_prosody_features(self, audio_data, pitch_track, peak_times):
        """Prosody: pitch contour slope, rhythm regularity, emphasis index."""
        # Contour slope (Hz/sec) via linear fit of F0 over time
        contour_slope = 0.0
        if pitch_track and len(pitch_track) >= 3:
            times = np.array([t for t, _ in pitch_track], dtype=float)
            f0s = np.array([f for _, f in pitch_track], dtype=float)
            # np.polyfit deg 1 → slope
            slope, _intercept = np.polyfit(times, f0s, 1)
            contour_slope = float(slope)

        # Rhythm regularity from inter-peak intervals (1 = perfectly regular)
        rhythm_regularity = 0.0
        if peak_times and len(peak_times) >= 3:
            intervals = np.diff(np.array(peak_times, dtype=float))
            intervals = intervals[intervals > 0.05]
            if len(intervals) >= 2:
                cv = float(np.std(intervals) / (np.mean(intervals) + 1e-6))
                rhythm_regularity = float(1.0 / (1.0 + cv))

        # Emphasis: top-decile frame energy vs median speech-frame energy
        frame_length = int(0.025 * self.sample_rate)
        hop_length = int(0.010 * self.sample_rate)
        energies = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            energies.append(float(np.sum(audio_data[i : i + frame_length] ** 2)))
        energies = np.array(energies)
        emphasis = 0.0
        if len(energies) > 4:
            thr = float(np.mean(energies) * 0.5)
            speech_e = energies[energies > thr]
            if len(speech_e) > 4:
                median_e = float(np.median(speech_e))
                top = float(np.percentile(speech_e, 90))
                emphasis = top / (median_e + 1e-12)

        return {
            "prosody_contour_slope": float(contour_slope),
            "prosody_rhythm_regularity": float(rhythm_regularity),
            "prosody_emphasis": float(emphasis),
        }

    def _extract_articulation_features(self, audio_data):
        """
        Articulation acoustic proxies.

        articulation_clarity: mid/high band energy vs low band (consonant detail)
        slur_index: slow spectral change during active speech (higher = more slurred)
        over_articulation_index: high clarity combined with strong emphasis peaks
        """
        if len(audio_data) < 16:
            return {
                "spectral_centroid_hz": 0.0,
                "articulation_clarity": 0.0,
                "slur_index": 0.0,
                "over_articulation_index": 0.0,
            }

        fft_data = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1 / self.sample_rate)
        mags = np.abs(fft_data)
        total = float(np.sum(mags)) + 1e-12
        spectral_centroid = float(np.sum(freqs * mags) / total)

        low = float(np.sum(mags[(freqs >= 80) & (freqs < 1000)]))
        mid_high = float(np.sum(mags[(freqs >= 2000) & (freqs <= 8000)]))
        clarity = mid_high / (low + 1e-12)

        # Slur: inverse of mean spectral flux on active frames
        frame_length = int(0.040 * self.sample_rate)
        hop_length = int(0.020 * self.sample_rate)
        fluxes = []
        prev = None
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i : i + frame_length]
            if np.max(np.abs(frame)) < 0.01:
                prev = None
                continue
            spec = np.abs(np.fft.rfft(frame))
            if prev is not None and len(prev) == len(spec):
                fluxes.append(float(np.mean(np.abs(spec - prev))))
            prev = spec
        mean_flux = float(np.mean(fluxes)) if fluxes else 0.0
        slur = float(1.0 / (1.0 + mean_flux))

        # Over-articulation: elevated clarity with strong peak factor
        rms = float(np.sqrt(np.mean(audio_data**2))) + 1e-12
        peak = float(np.max(np.abs(audio_data)))
        peak_factor = peak / rms
        over_art = float(clarity * min(peak_factor / 8.0, 2.0))

        return {
            "spectral_centroid_hz": spectral_centroid,
            "articulation_clarity": float(clarity),
            "slur_index": slur,
            "over_articulation_index": over_art,
        }

    # Back-compat alias used by older call sites / docs
    def _extract_stress_indicators(self, audio_data):
        return self._extract_voice_quality(audio_data, pitch_track=None)

    def _calculate_stress_level(self, features):
        """
        Composite Stress Index (0-100).

        Sums weighted contributions from five vocal biomarkers. Each factor
        has two tiers (moderate / high) so the score ramps gradually rather
        than flipping binary. Capped at 100.

        Used for: patient trend lines, clinician alerts, Claude AI context.
        Lower is calmer; higher suggests hyperarousal or vocal tension.

        Factor weights (max points):
          pitch_variation ........ 25
          speaking_rate .......... 25
          high_frequency_ratio ... 20
          energy_variance ........ 15
          jitter ................. 15
        """
        stress_score = 0

        # Unstable pitch — one of the strongest stress correlates in voice research
        pitch_var = features.get("pitch_variation", 0)
        if pitch_var > 0.15:
            stress_score += 25
        elif pitch_var > 0.08:
            stress_score += 15

        # Rapid speech — hyperarousal / anxiety indicator
        speaking_rate = features.get("speaking_rate", 0)
        if speaking_rate > 5.0:
            stress_score += 25
        elif speaking_rate > 3.5:
            stress_score += 15

        # Elevated high-frequency energy — vocal strain / tension
        high_freq_ratio = features.get("high_frequency_ratio", 0)
        if high_freq_ratio > 0.4:
            stress_score += 20
        elif high_freq_ratio > 0.25:
            stress_score += 10

        # Erratic loudness swings across the clip
        energy_var = features.get("energy_variance", 0)
        if energy_var > 0.001:
            stress_score += 15
        elif energy_var > 0.0005:
            stress_score += 10

        # Micro-level amplitude instability (voice jitter)
        jitter = features.get("jitter", 0)
        if jitter > 0.05:
            stress_score += 15
        elif jitter > 0.02:
            stress_score += 10

        return min(100, stress_score)

    def _calculate_enhanced_score(self, features):
        """
        Composite Behavioral Score (0-100).

        Starts at a neutral baseline (50) and rewards healthy engagement signals:
        adequate energy, active speech, stable pitch, and normal speaking rate.
        High stress_level deducts up to 20 points — behavioral wellness and
        stress are inversely related in this model.

        Used for: longitudinal "how is the subject doing?" dashboards.
        """
        score = 50

        # Sufficient vocal energy suggests the subject is engaged / responsive
        rms = features.get("rms_energy", 0)
        if rms > 0.05:
            score += 15
        elif rms > 0.02:
            score += 10
        elif rms > 0.01:
            score += 5

        # Active speech time — very low ratio may indicate withdrawal / flat affect
        speech_ratio = features.get("speech_ratio", 0)
        if speech_ratio > 0.5:
            score += 15
        elif speech_ratio > 0.3:
            score += 10

        # Reward pitch stability (inverse of stress pitch_variation)
        pitch_var = features.get("pitch_variation", 0)
        if pitch_var < 0.05:
            score += 10
        elif pitch_var < 0.10:
            score += 5

        # Conversational speaking rate (2-4 syllables/sec) is treated as healthy
        speaking_rate = features.get("speaking_rate", 0)
        if 2.0 <= speaking_rate <= 4.0:
            score += 10

        # Pull score down when composite stress is elevated
        stress_level = features.get("stress_level", 0)
        score -= int(stress_level * 0.2)

        return max(0, min(100, score))


def compute_voice_activity(
    audio_data: np.ndarray,
    sample_rate: int,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
) -> tuple[np.ndarray, float, np.ndarray]:
    """
    Helper for audio_analyzer visualizations (not used in scoring).

    Returns frame energies, the VAD threshold, and a boolean mask of speech frames
    for plotting the voice-activity chart saved alongside each analysis.
    """
    frame_length = int(frame_ms * sample_rate / 1000)
    hop_length = int(hop_ms * sample_rate / 1000)

    frame_energies = []
    for i in range(0, len(audio_data) - frame_length, hop_length):
        frame = audio_data[i : i + frame_length]
        frame_energies.append(float(np.sum(frame**2)))

    frame_energies_arr = np.array(frame_energies)
    threshold = float(np.mean(frame_energies_arr) * 0.5) if len(frame_energies_arr) else 0.0
    speech_frames = frame_energies_arr > threshold
    return frame_energies_arr, threshold, speech_frames


def print_feature_summary(features: dict) -> None:
    """Console output aligned to the researcher acoustic feature set."""
    print("1️⃣ Pitch (F0):")
    print(f"   F0 / pitch_mean: {features.get('f0_mean', features.get('pitch_mean', 0)):.1f} Hz")
    print(f"   Pitch std / variability: {features.get('pitch_std', 0):.1f} Hz  (CV {features.get('pitch_variation', 0):.3f})")
    print(f"   Pitch range: {features.get('pitch_range', 0):.1f} Hz")
    print()

    print("2️⃣ Speech rate:")
    print(f"   Syllables/sec: {features.get('speaking_rate', 0):.2f}")
    print(f"   Words/min (acoustic proxy): {features.get('speaking_rate_wpm', 0):.1f}")
    print(f"   Response / onset latency: {features.get('response_latency_sec', 0):.3f} sec")
    print()

    print("3️⃣ Intensity:")
    print(f"   RMS energy: {features.get('rms_energy', 0):.4f}")
    print(f"   Peak amplitude: {features.get('peak_amplitude', 0):.4f}")
    print(f"   Peak-to-average ratio: {features.get('peak_to_average_ratio', features.get('dynamic_range', 0)):.2f}x")
    print()

    print("4️⃣ Voice quality:")
    print(f"   Tension: {features.get('tension', 0):.3f}")
    print(f"   Roughness: {features.get('roughness', 0):.4f}")
    print(f"   Jitter: {features.get('jitter', 0):.4f}")
    print(f"   Shimmer: {features.get('shimmer', 0):.4f}")
    print(f"   Spectral flux: {features.get('spectral_flux', 0):.2f}")
    print()

    print("5️⃣ Pauses / disfluencies (acoustic):")
    print(f"   Pause ratio: {features.get('pause_ratio', 0):.1%}")
    print(f"   Pause count: {features.get('pause_count', 0)}")
    print(f"   Mean / max pause: {features.get('mean_pause_duration_sec', 0):.3f}s / {features.get('max_pause_duration_sec', 0):.3f}s")
    print(f"   Cutoff rate: {features.get('cutoff_rate_per_min', 0):.2f} / min")
    print(f"   Filler proxy rate: {features.get('filler_proxy_rate_per_min', 0):.2f} / min")
    print("   (Lexical fillers need ASR — filler_proxy is audio-only)")
    print()

    print("6️⃣ Prosody:")
    print(f"   Contour slope: {features.get('prosody_contour_slope', 0):.2f} Hz/sec")
    print(f"   Rhythm regularity: {features.get('prosody_rhythm_regularity', 0):.3f}")
    print(f"   Emphasis index: {features.get('prosody_emphasis', 0):.2f}")
    print()

    print("7️⃣ Articulation:")
    print(f"   Spectral centroid: {features.get('spectral_centroid_hz', 0):.1f} Hz")
    print(f"   Clarity: {features.get('articulation_clarity', 0):.3f}")
    print(f"   Slur index: {features.get('slur_index', 0):.3f}")
    print(f"   Over-articulation: {features.get('over_articulation_index', 0):.3f}")
    print()

    behavioral_score = int(features.get("behavioral_score", 0))
    stress_level = int(features.get("stress_level", 0))
    print("8️⃣ Assessment:")
    print(f"   Behavioral Score: {behavioral_score}/100")
    print(f"   Stress Level: {stress_level}/100")
    print(f"   Vocal stability: {features.get('vocal_stability', 0):.3f}")
    if behavioral_score >= 80:
        status = "Excellent"
    elif behavioral_score >= 60:
        status = "Good"
    elif behavioral_score >= 40:
        status = "Fair"
    else:
        status = "Low Activity"
    print(f"   Status: {status}")
    print()


def test_enhanced_extraction():
    """Synthetic stressed-voice test — run: python enhanced_features.py"""
    print("=" * 70)
    print("ENHANCED FEATURE EXTRACTION TEST")
    print("=" * 70)
    print()

    sample_rate = 44100
    duration = 3
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Simulated stressed voice: wandering pitch + noise
    base_freq = 200
    pitch_variation = np.random.normal(0, 30, len(t))
    audio = np.sin(2 * np.pi * (base_freq + pitch_variation) * t)
    audio += np.random.normal(0, 0.1, len(t))
    audio *= 0.3

    extractor = EnhancedFeatureExtractor(sample_rate)
    features = extractor.extract_all_features(audio)

    print("EXTRACTED FEATURES (researcher acoustic set):")
    print()
    print_feature_summary(features)

    print("=" * 70)
    print("Enhanced feature extraction test complete!")
    print("=" * 70)
    return features


if __name__ == "__main__":
    try:
        from audio_utils import configure_stdio

        configure_stdio()
    except Exception:
        pass
    test_enhanced_extraction()
