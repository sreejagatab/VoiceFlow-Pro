"""
Advanced Audio Processing for VoiceFlow Pro

This module provides sophisticated audio processing capabilities including:
- Real-time noise suppression
- Automatic gain control
- Echo cancellation
- Audio quality enhancement
- Dynamic audio optimization
- Real-time audio analysis
"""

import asyncio
import logging
import numpy as np
import scipy.signal
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import librosa
import soundfile as sf
from livekit import rtc

logger = logging.getLogger(__name__)


class AudioProcessingMode(Enum):
    """Audio processing modes"""
    VOICE_CHAT = "voice_chat"          # Optimized for conversation
    CONFERENCE = "conference"          # Optimized for multi-participant
    BROADCAST = "broadcast"            # Optimized for one-to-many
    MUSIC = "music"                    # Optimized for music/media
    NOISE_REDUCTION = "noise_reduction" # Aggressive noise reduction


class NoiseType(Enum):
    """Types of noise detected"""
    BACKGROUND_NOISE = "background_noise"
    KEYBOARD_TYPING = "keyboard_typing"
    TRAFFIC = "traffic"
    HVAC = "hvac"
    ELECTRICAL_HUM = "electrical_hum"
    WIND = "wind"
    ECHO = "echo"
    UNKNOWN = "unknown"


@dataclass
class AudioMetrics:
    """Real-time audio quality metrics"""
    # Signal quality
    signal_to_noise_ratio: float
    dynamic_range: float
    peak_level: float
    rms_level: float
    
    # Frequency analysis
    spectral_centroid: float
    spectral_rolloff: float
    zero_crossing_rate: float
    
    # Noise characteristics
    noise_floor: float
    detected_noise_types: List[NoiseType]
    noise_reduction_applied: float
    
    # Quality indicators
    clarity_score: float
    naturalness_score: float
    intelligibility_score: float
    
    # Processing metrics
    latency_ms: float
    cpu_usage_percent: float
    
    # Timestamp
    measured_at: datetime


@dataclass
class AudioProcessingSettings:
    """Audio processing configuration"""
    # Noise suppression
    noise_suppression_enabled: bool
    noise_suppression_strength: float  # 0.0 to 1.0
    adaptive_noise_suppression: bool
    
    # Gain control
    auto_gain_control: bool
    target_level_db: float
    max_gain_db: float
    gain_smoothing: float
    
    # Echo cancellation
    echo_cancellation_enabled: bool
    echo_delay_ms: int
    echo_suppression_db: float
    
    # Equalization
    eq_enabled: bool
    eq_bands: Dict[str, float]  # Frequency bands and gains
    
    # Dynamic processing
    compressor_enabled: bool
    compressor_ratio: float
    compressor_threshold_db: float
    
    # Quality enhancement
    voice_enhancement: bool
    breath_reduction: bool
    de_essing: bool
    
    # Real-time adaptation
    adaptive_processing: bool
    learning_rate: float


class AdvancedAudioProcessor:
    """
    Advanced real-time audio processing engine
    """
    
    def __init__(self, sample_rate: int = 16000, buffer_size: int = 1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Processing settings
        self.settings = AudioProcessingSettings(
            noise_suppression_enabled=True,
            noise_suppression_strength=0.7,
            adaptive_noise_suppression=True,
            auto_gain_control=True,
            target_level_db=-20.0,
            max_gain_db=30.0,
            gain_smoothing=0.95,
            echo_cancellation_enabled=True,
            echo_delay_ms=50,
            echo_suppression_db=40.0,
            eq_enabled=True,
            eq_bands={
                "low": 0.0,      # 80-250 Hz
                "mid_low": 2.0,  # 250-800 Hz (voice clarity)
                "mid": 3.0,      # 800-2500 Hz (main voice)
                "mid_high": 1.0, # 2500-8000 Hz (consonants)
                "high": -2.0     # 8000+ Hz (sibilance reduction)
            },
            compressor_enabled=True,
            compressor_ratio=3.0,
            compressor_threshold_db=-25.0,
            voice_enhancement=True,
            breath_reduction=True,
            de_essing=True,
            adaptive_processing=True,
            learning_rate=0.01
        )
        
        # Audio analysis buffers
        self.audio_buffer = np.zeros(sample_rate * 2)  # 2 second buffer
        self.noise_profile = np.zeros(512)  # Noise spectral profile
        self.echo_buffer = np.zeros(sample_rate)  # 1 second echo buffer
        
        # Processing state
        self.gain_smoothed = 1.0
        self.noise_gate_state = False
        self.compressor_envelope = 0.0
        self.adaptation_history = []
        
        # Metrics tracking
        self.metrics_history: List[AudioMetrics] = []
        self.processing_stats = {
            "total_samples_processed": 0,
            "noise_reduction_events": 0,
            "gain_adjustments": 0,
            "echo_cancellations": 0
        }
        
        # Frequency analysis setup
        self._setup_frequency_analysis()
        
        # Adaptive learning
        self.environment_model = {
            "noise_characteristics": {},
            "room_acoustics": {},
            "user_voice_profile": {}
        }
    
    def _setup_frequency_analysis(self):
        """Initialize frequency analysis components"""
        # FFT parameters
        self.fft_size = 512
        self.hop_length = 256
        self.window = np.hanning(self.fft_size)
        
        # Frequency bands for EQ
        self.freq_bins = np.fft.fftfreq(self.fft_size, 1/self.sample_rate)
        self.eq_filters = self._design_eq_filters()
        
        # Noise reduction filters
        self.wiener_filter = np.ones(self.fft_size // 2 + 1)
        
        # Voice activity detection
        self.vad_threshold = 0.01
        self.vad_history = np.zeros(10)
    
    def _design_eq_filters(self) -> Dict[str, np.ndarray]:
        """Design EQ filters for different frequency bands"""
        filters = {}
        
        # Define frequency ranges
        bands = {
            "low": (80, 250),
            "mid_low": (250, 800),
            "mid": (800, 2500),
            "mid_high": (2500, 8000),
            "high": (8000, self.sample_rate // 2)
        }
        
        for band_name, (low_freq, high_freq) in bands.items():
            # Create bandpass filter
            nyquist = self.sample_rate / 2
            low_norm = low_freq / nyquist
            high_norm = min(high_freq / nyquist, 0.99)
            
            if low_norm < 0.99 and high_norm > low_norm:
                b, a = scipy.signal.butter(4, [low_norm, high_norm], btype='band')
                filters[band_name] = (b, a)
            else:
                # Handle edge cases
                filters[band_name] = (np.array([1.0]), np.array([1.0]))
        
        return filters
    
    async def process_audio_stream(self, audio_data: np.ndarray,
                                 processing_mode: AudioProcessingMode = AudioProcessingMode.VOICE_CHAT) -> Tuple[np.ndarray, AudioMetrics]:
        """
        Process incoming audio stream with advanced algorithms
        """
        start_time = datetime.now()
        
        # Ensure audio is float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Store original for comparison
        original_audio = audio_data.copy()
        
        # Update processing mode settings
        await self._adapt_settings_for_mode(processing_mode)
        
        # Step 1: Analyze incoming audio
        analysis_metrics = await self._analyze_audio_quality(audio_data)
        
        # Step 2: Noise suppression
        if self.settings.noise_suppression_enabled:
            audio_data = await self._apply_noise_suppression(audio_data)
        
        # Step 3: Echo cancellation
        if self.settings.echo_cancellation_enabled:
            audio_data = await self._apply_echo_cancellation(audio_data)
        
        # Step 4: Automatic gain control
        if self.settings.auto_gain_control:
            audio_data = await self._apply_automatic_gain_control(audio_data)
        
        # Step 5: Dynamic range compression
        if self.settings.compressor_enabled:
            audio_data = await self._apply_compression(audio_data)
        
        # Step 6: Equalization
        if self.settings.eq_enabled:
            audio_data = await self._apply_equalization(audio_data)
        
        # Step 7: Voice enhancement
        if self.settings.voice_enhancement:
            audio_data = await self._apply_voice_enhancement(audio_data)
        
        # Step 8: Adaptive learning
        if self.settings.adaptive_processing:
            await self._update_adaptive_models(original_audio, audio_data)
        
        # Calculate processing metrics
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Generate comprehensive metrics
        metrics = await self._generate_processing_metrics(
            original_audio, audio_data, analysis_metrics, processing_time
        )
        
        # Update statistics
        self.processing_stats["total_samples_processed"] += len(audio_data)
        
        return audio_data, metrics
    
    async def _adapt_settings_for_mode(self, mode: AudioProcessingMode):
        """Adapt processing settings based on mode"""
        mode_settings = {
            AudioProcessingMode.VOICE_CHAT: {
                "noise_suppression_strength": 0.8,
                "target_level_db": -20.0,
                "compressor_ratio": 3.0,
                "voice_enhancement": True
            },
            AudioProcessingMode.CONFERENCE: {
                "noise_suppression_strength": 0.9,
                "target_level_db": -18.0,
                "compressor_ratio": 4.0,
                "voice_enhancement": True
            },
            AudioProcessingMode.BROADCAST: {
                "noise_suppression_strength": 0.95,
                "target_level_db": -16.0,
                "compressor_ratio": 6.0,
                "voice_enhancement": True
            },
            AudioProcessingMode.NOISE_REDUCTION: {
                "noise_suppression_strength": 0.95,
                "target_level_db": -22.0,
                "compressor_ratio": 2.0,
                "voice_enhancement": False
            }
        }
        
        if mode in mode_settings:
            for key, value in mode_settings[mode].items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
    
    async def _analyze_audio_quality(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Analyze audio quality metrics"""
        
        # Basic signal metrics
        rms_level = np.sqrt(np.mean(audio_data ** 2))
        peak_level = np.max(np.abs(audio_data))
        
        # Spectral analysis
        if len(audio_data) >= self.fft_size:
            # Compute STFT
            f, t, stft = scipy.signal.stft(
                audio_data, fs=self.sample_rate, 
                window=self.window, nperseg=self.fft_size,
                noverlap=self.fft_size//2
            )
            
            magnitude = np.abs(stft)
            
            # Spectral features
            spectral_centroid = np.sum(f[:, np.newaxis] * magnitude, axis=0) / (np.sum(magnitude, axis=0) + 1e-8)
            spectral_rolloff = self._calculate_spectral_rolloff(f, magnitude)
            
            # Zero crossing rate
            zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
            zero_crossing_rate = zero_crossings / len(audio_data)
            
            # Noise floor estimation
            noise_floor = np.percentile(magnitude, 10)
            
        else:
            # Handle short audio segments
            spectral_centroid = np.array([0.0])
            spectral_rolloff = np.array([0.0])
            zero_crossing_rate = 0.0
            noise_floor = 0.0
        
        # Signal-to-noise ratio estimation
        signal_power = rms_level ** 2
        noise_power = noise_floor ** 2
        snr = 10 * np.log10(signal_power / (noise_power + 1e-8))
        
        return {
            "rms_level": float(rms_level),
            "peak_level": float(peak_level),
            "spectral_centroid": float(np.mean(spectral_centroid)),
            "spectral_rolloff": float(np.mean(spectral_rolloff)),
            "zero_crossing_rate": float(zero_crossing_rate),
            "noise_floor": float(noise_floor),
            "snr": float(snr)
        }
    
    def _calculate_spectral_rolloff(self, f: np.ndarray, magnitude: np.ndarray, 
                                  rolloff_percent: float = 0.85) -> np.ndarray:
        """Calculate spectral rolloff frequency"""
        cumulative_energy = np.cumsum(magnitude ** 2, axis=0)
        total_energy = cumulative_energy[-1, :]
        
        rolloff_threshold = rolloff_percent * total_energy
        rolloff_indices = np.argmax(cumulative_energy >= rolloff_threshold[np.newaxis, :], axis=0)
        
        return f[rolloff_indices]
    
    async def _apply_noise_suppression(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction noise suppression"""
        
        if len(audio_data) < self.fft_size:
            return audio_data
        
        # Compute STFT
        f, t, stft = scipy.signal.stft(
            audio_data, fs=self.sample_rate,
            window=self.window, nperseg=self.fft_size,
            noverlap=self.fft_size//2
        )
        
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        # Update noise profile (use first few frames or silent periods)
        vad = self._detect_voice_activity(magnitude)
        if not np.any(vad[:5]):  # First 5 frames are likely noise
            self.noise_profile = np.mean(magnitude[:, :5], axis=1)
        
        # Apply Wiener filtering
        noise_power = self.noise_profile[:, np.newaxis] ** 2
        signal_power = magnitude ** 2
        
        # Wiener filter
        wiener_gain = signal_power / (signal_power + noise_power + 1e-8)
        
        # Apply smoothing and strength control
        strength = self.settings.noise_suppression_strength
        wiener_gain = wiener_gain ** strength
        
        # Minimum gain to preserve naturalness
        min_gain = 0.1
        wiener_gain = np.maximum(wiener_gain, min_gain)
        
        # Apply filter
        filtered_magnitude = magnitude * wiener_gain
        filtered_stft = filtered_magnitude * np.exp(1j * phase)
        
        # Inverse STFT
        _, filtered_audio = scipy.signal.istft(
            filtered_stft, fs=self.sample_rate,
            window=self.window, nperseg=self.fft_size,
            noverlap=self.fft_size//2
        )
        
        # Ensure same length as input
        if len(filtered_audio) != len(audio_data):
            filtered_audio = np.resize(filtered_audio, len(audio_data))
        
        self.processing_stats["noise_reduction_events"] += 1
        
        return filtered_audio.astype(np.float32)
    
    def _detect_voice_activity(self, magnitude: np.ndarray) -> np.ndarray:
        """Simple voice activity detection"""
        energy = np.sum(magnitude ** 2, axis=0)
        energy_smooth = scipy.signal.medfilt(energy, kernel_size=3)
        
        # Adaptive threshold
        threshold = np.percentile(energy_smooth, 30) * 2
        vad = energy_smooth > threshold
        
        return vad
    
    async def _apply_echo_cancellation(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply acoustic echo cancellation"""
        
        # Simple echo cancellation using delay and subtract
        delay_samples = int(self.settings.echo_delay_ms * self.sample_rate / 1000)
        
        if delay_samples < len(audio_data):
            # Create delayed version
            delayed_audio = np.zeros_like(audio_data)
            delayed_audio[delay_samples:] = audio_data[:-delay_samples]
            
            # Estimate echo component
            echo_estimate = delayed_audio * 0.3  # Simple echo model
            
            # Subtract echo
            echo_cancelled = audio_data - echo_estimate
            
            # Apply gentle high-pass filter to remove low-frequency rumble
            b, a = scipy.signal.butter(2, 80.0 / (self.sample_rate / 2), btype='high')
            echo_cancelled = scipy.signal.filtfilt(b, a, echo_cancelled)
            
            self.processing_stats["echo_cancellations"] += 1
            
            return echo_cancelled.astype(np.float32)
        
        return audio_data
    
    async def _apply_automatic_gain_control(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply automatic gain control"""
        
        # Calculate current RMS level
        current_rms = np.sqrt(np.mean(audio_data ** 2))
        
        if current_rms > 1e-6:  # Avoid division by zero
            # Target level in linear scale
            target_linear = 10 ** (self.settings.target_level_db / 20)
            
            # Calculate required gain
            required_gain = target_linear / current_rms
            
            # Limit maximum gain
            max_gain_linear = 10 ** (self.settings.max_gain_db / 20)
            required_gain = min(required_gain, max_gain_linear)
            
            # Smooth gain changes
            smoothing = self.settings.gain_smoothing
            self.gain_smoothed = smoothing * self.gain_smoothed + (1 - smoothing) * required_gain
            
            # Apply gain
            gained_audio = audio_data * self.gain_smoothed
            
            # Prevent clipping
            peak = np.max(np.abs(gained_audio))
            if peak > 0.95:
                gained_audio = gained_audio * (0.95 / peak)
            
            self.processing_stats["gain_adjustments"] += 1
            
            return gained_audio.astype(np.float32)
        
        return audio_data
    
    async def _apply_compression(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply dynamic range compression"""
        
        # Convert to dB
        audio_db = 20 * np.log10(np.abs(audio_data) + 1e-8)
        
        # Threshold and ratio
        threshold_db = self.settings.compressor_threshold_db
        ratio = self.settings.compressor_ratio
        
        # Apply compression above threshold
        above_threshold = audio_db > threshold_db
        compressed_db = audio_db.copy()
        
        # Compress
        excess_db = audio_db - threshold_db
        compressed_excess = excess_db / ratio
        compressed_db[above_threshold] = threshold_db + compressed_excess[above_threshold]
        
        # Convert back to linear
        gain_db = compressed_db - audio_db
        gain_linear = 10 ** (gain_db / 20)
        
        # Smooth envelope
        attack_coeff = np.exp(-1 / (0.001 * self.sample_rate))  # 1ms attack
        release_coeff = np.exp(-1 / (0.1 * self.sample_rate))   # 100ms release
        
        envelope = np.zeros_like(gain_linear)
        envelope[0] = gain_linear[0]
        
        for i in range(1, len(gain_linear)):
            if gain_linear[i] < envelope[i-1]:
                # Attack
                envelope[i] = attack_coeff * envelope[i-1] + (1 - attack_coeff) * gain_linear[i]
            else:
                # Release
                envelope[i] = release_coeff * envelope[i-1] + (1 - release_coeff) * gain_linear[i]
        
        # Apply envelope
        compressed_audio = audio_data * envelope
        
        return compressed_audio.astype(np.float32)
    
    async def _apply_equalization(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply multi-band equalization"""
        
        eq_audio = audio_data.copy()
        
        # Apply each EQ band
        for band_name, gain_db in self.settings.eq_bands.items():
            if band_name in self.eq_filters and abs(gain_db) > 0.1:
                b, a = self.eq_filters[band_name]
                
                # Apply filter
                try:
                    filtered = scipy.signal.filtfilt(b, a, eq_audio)
                    
                    # Apply gain
                    gain_linear = 10 ** (gain_db / 20)
                    eq_audio = eq_audio + (filtered - eq_audio) * (gain_linear - 1)
                    
                except Exception as e:
                    logger.warning(f"EQ filter failed for band {band_name}: {e}")
                    continue
        
        return eq_audio.astype(np.float32)
    
    async def _apply_voice_enhancement(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply voice-specific enhancements"""
        
        enhanced_audio = audio_data.copy()
        
        # Breath reduction
        if self.settings.breath_reduction:
            enhanced_audio = await self._reduce_breath_sounds(enhanced_audio)
        
        # De-essing (reduce harsh 's' sounds)
        if self.settings.de_essing:
            enhanced_audio = await self._apply_de_essing(enhanced_audio)
        
        # Voice clarity enhancement
        enhanced_audio = await self._enhance_voice_clarity(enhanced_audio)
        
        return enhanced_audio
    
    async def _reduce_breath_sounds(self, audio_data: np.ndarray) -> np.ndarray:
        """Reduce breath sounds"""
        
        # High-pass filter to identify breath-like sounds
        b, a = scipy.signal.butter(4, 150.0 / (self.sample_rate / 2), btype='high')
        high_freq = scipy.signal.filtfilt(b, a, audio_data)
        
        # Detect breath sounds (high frequency, low amplitude)
        breath_threshold = np.percentile(np.abs(high_freq), 70)
        breath_mask = (np.abs(high_freq) > breath_threshold) & (np.abs(audio_data) < 0.1)
        
        # Gentle attenuation of breath sounds
        breath_reduced = audio_data.copy()
        breath_reduced[breath_mask] *= 0.3
        
        return breath_reduced.astype(np.float32)
    
    async def _apply_de_essing(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply de-essing to reduce harsh sibilants"""
        
        # Detect sibilant frequencies (4-8 kHz)
        b, a = scipy.signal.butter(4, [4000.0, 8000.0], 
                                 btype='band', fs=self.sample_rate)
        sibilant_band = scipy.signal.filtfilt(b, a, audio_data)
        
        # Dynamic de-essing based on sibilant energy
        sibilant_energy = np.abs(sibilant_band)
        sibilant_threshold = np.percentile(sibilant_energy, 85)
        
        # Create de-essing gain
        de_ess_gain = np.ones_like(audio_data)
        sibilant_mask = sibilant_energy > sibilant_threshold
        de_ess_gain[sibilant_mask] = 0.6  # Reduce by 40%
        
        # Smooth the gain
        de_ess_gain = scipy.signal.medfilt(de_ess_gain, kernel_size=5)
        
        return (audio_data * de_ess_gain).astype(np.float32)
    
    async def _enhance_voice_clarity(self, audio_data: np.ndarray) -> np.ndarray:
        """Enhance voice clarity and presence"""
        
        # Enhance vocal formants (800-2500 Hz)
        b, a = scipy.signal.butter(4, [800.0, 2500.0], 
                                 btype='band', fs=self.sample_rate)
        vocal_formants = scipy.signal.filtfilt(b, a, audio_data)
        
        # Gentle boost
        enhanced = audio_data + vocal_formants * 0.15
        
        # Prevent clipping
        peak = np.max(np.abs(enhanced))
        if peak > 0.95:
            enhanced = enhanced * (0.95 / peak)
        
        return enhanced.astype(np.float32)
    
    async def _update_adaptive_models(self, original_audio: np.ndarray, 
                                    processed_audio: np.ndarray):
        """Update adaptive learning models"""
        
        # Analyze improvement metrics
        original_snr = self._calculate_snr(original_audio)
        processed_snr = self._calculate_snr(processed_audio)
        
        improvement = processed_snr - original_snr
        
        # Store adaptation history
        adaptation_entry = {
            "timestamp": datetime.now(),
            "snr_improvement": improvement,
            "settings_snapshot": asdict(self.settings)
        }
        
        self.adaptation_history.append(adaptation_entry)
        
        # Keep only recent history
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]
        
        # Adapt settings based on performance
        if len(self.adaptation_history) >= 10:
            await self._adapt_processing_settings()
    
    def _calculate_snr(self, audio_data: np.ndarray) -> float:
        """Calculate signal-to-noise ratio"""
        signal_power = np.mean(audio_data ** 2)
        noise_power = np.percentile(audio_data ** 2, 10)  # Estimate noise floor
        
        if noise_power > 0:
            return 10 * np.log10(signal_power / noise_power)
        else:
            return 60.0  # High SNR if no noise detected
    
    async def _adapt_processing_settings(self):
        """Adapt processing settings based on performance history"""
        
        recent_improvements = [entry["snr_improvement"] for entry in self.adaptation_history[-10:]]
        avg_improvement = np.mean(recent_improvements)
        
        learning_rate = self.settings.learning_rate
        
        # Adapt noise suppression strength
        if avg_improvement < 1.0:  # Poor improvement
            self.settings.noise_suppression_strength = min(
                0.95, self.settings.noise_suppression_strength + learning_rate
            )
        elif avg_improvement > 3.0:  # Good improvement, maybe too aggressive
            self.settings.noise_suppression_strength = max(
                0.3, self.settings.noise_suppression_strength - learning_rate
            )
    
    async def _generate_processing_metrics(self, original_audio: np.ndarray,
                                         processed_audio: np.ndarray,
                                         analysis_metrics: Dict[str, float],
                                         processing_time_ms: float) -> AudioMetrics:
        """Generate comprehensive processing metrics"""
        
        # Quality assessments
        clarity_score = await self._assess_clarity(processed_audio)
        naturalness_score = await self._assess_naturalness(original_audio, processed_audio)
        intelligibility_score = await self._assess_intelligibility(processed_audio)
        
        # Detect noise types
        detected_noise_types = await self._detect_noise_types(original_audio)
        
        # Calculate noise reduction applied
        original_noise = np.percentile(np.abs(original_audio), 10)
        processed_noise = np.percentile(np.abs(processed_audio), 10)
        noise_reduction = max(0, (original_noise - processed_noise) / (original_noise + 1e-8))
        
        # CPU usage (simplified)
        cpu_usage = min(100.0, processing_time_ms / 10)  # Rough estimate
        
        metrics = AudioMetrics(
            signal_to_noise_ratio=analysis_metrics["snr"],
            dynamic_range=20 * np.log10(analysis_metrics["peak_level"] / (analysis_metrics["rms_level"] + 1e-8)),
            peak_level=analysis_metrics["peak_level"],
            rms_level=analysis_metrics["rms_level"],
            spectral_centroid=analysis_metrics["spectral_centroid"],
            spectral_rolloff=analysis_metrics["spectral_rolloff"],
            zero_crossing_rate=analysis_metrics["zero_crossing_rate"],
            noise_floor=analysis_metrics["noise_floor"],
            detected_noise_types=detected_noise_types,
            noise_reduction_applied=noise_reduction,
            clarity_score=clarity_score,
            naturalness_score=naturalness_score,
            intelligibility_score=intelligibility_score,
            latency_ms=processing_time_ms,
            cpu_usage_percent=cpu_usage,
            measured_at=datetime.now()
        )
        
        # Store metrics
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return metrics
    
    async def _assess_clarity(self, audio_data: np.ndarray) -> float:
        """Assess voice clarity score"""
        
        # High-frequency content indicates clarity
        b, a = scipy.signal.butter(4, 2000.0 / (self.sample_rate / 2), btype='high')
        high_freq = scipy.signal.filtfilt(b, a, audio_data)
        
        # Clarity based on high-frequency energy
        hf_energy = np.mean(high_freq ** 2)
        total_energy = np.mean(audio_data ** 2)
        
        clarity_ratio = hf_energy / (total_energy + 1e-8)
        clarity_score = min(1.0, clarity_ratio * 5)  # Scale to 0-1
        
        return clarity_score
    
    async def _assess_naturalness(self, original_audio: np.ndarray, 
                                processed_audio: np.ndarray) -> float:
        """Assess naturalness by comparing to original"""
        
        # Calculate spectral similarity
        if len(original_audio) >= self.fft_size and len(processed_audio) >= self.fft_size:
            # Compute spectrograms
            _, _, stft_orig = scipy.signal.stft(original_audio, fs=self.sample_rate, nperseg=self.fft_size)
            _, _, stft_proc = scipy.signal.stft(processed_audio, fs=self.sample_rate, nperseg=self.fft_size)
            
            # Spectral correlation
            mag_orig = np.abs(stft_orig).flatten()
            mag_proc = np.abs(stft_proc).flatten()
            
            # Ensure same length
            min_len = min(len(mag_orig), len(mag_proc))
            mag_orig = mag_orig[:min_len]
            mag_proc = mag_proc[:min_len]
            
            if len(mag_orig) > 0:
                correlation = np.corrcoef(mag_orig, mag_proc)[0, 1]
                naturalness = max(0, correlation)
            else:
                naturalness = 0.8  # Default for short segments
        else:
            naturalness = 0.8  # Default for short segments
        
        return naturalness
    
    async def _assess_intelligibility(self, audio_data: np.ndarray) -> float:
        """Assess speech intelligibility"""
        
        # Focus on speech critical bands (300-3000 Hz)
        b, a = scipy.signal.butter(4, [300.0, 3000.0], 
                                 btype='band', fs=self.sample_rate)
        speech_band = scipy.signal.filtfilt(b, a, audio_data)
        
        # Calculate speech energy ratio
        speech_energy = np.mean(speech_band ** 2)
        total_energy = np.mean(audio_data ** 2)
        
        intelligibility_ratio = speech_energy / (total_energy + 1e-8)
        intelligibility_score = min(1.0, intelligibility_ratio * 2)
        
        return intelligibility_score
    
    async def _detect_noise_types(self, audio_data: np.ndarray) -> List[NoiseType]:
        """Detect types of noise present in audio"""
        
        detected_types = []
        
        if len(audio_data) < self.fft_size:
            return detected_types
        
        # Spectral analysis
        f, t, stft = scipy.signal.stft(audio_data, fs=self.sample_rate, nperseg=self.fft_size)
        magnitude = np.abs(stft)
        
        # Frequency-based noise detection
        low_freq_energy = np.mean(magnitude[f < 200])
        mid_freq_energy = np.mean(magnitude[(f >= 200) & (f < 2000)])
        high_freq_energy = np.mean(magnitude[f >= 2000])
        
        total_energy = low_freq_energy + mid_freq_energy + high_freq_energy
        
        if total_energy > 0:
            # HVAC/Air conditioning (low frequency hum)
            if low_freq_energy / total_energy > 0.6:
                detected_types.append(NoiseType.HVAC)
            
            # Keyboard typing (sharp transients in mid-high frequencies)
            # Look for repetitive patterns
            if self._detect_periodic_transients(magnitude, f):
                detected_types.append(NoiseType.KEYBOARD_TYPING)
            
            # Electrical hum (60Hz and harmonics)
            if self._detect_electrical_hum(magnitude, f):
                detected_types.append(NoiseType.ELECTRICAL_HUM)
            
            # Wind (broadband noise with specific characteristics)
            if self._detect_wind_noise(magnitude, f):
                detected_types.append(NoiseType.WIND)
            
            # Traffic (rolling broadband noise)
            if self._detect_traffic_noise(magnitude, f):
                detected_types.append(NoiseType.TRAFFIC)
        
        # If noise detected but no specific type, mark as unknown
        noise_level = np.percentile(magnitude, 50)
        if noise_level > 0.01 and not detected_types:
            detected_types.append(NoiseType.BACKGROUND_NOISE)
        
        return detected_types
    
    def _detect_periodic_transients(self, magnitude: np.ndarray, f: np.ndarray) -> bool:
        """Detect periodic transients like keyboard typing"""
        
        # Look for sharp peaks in mid-high frequencies
        mid_high_band = magnitude[(f >= 1000) & (f < 8000)]
        
        if len(mid_high_band) == 0:
            return False
        
        # Calculate temporal variation
        temporal_variation = np.std(np.mean(mid_high_band, axis=0))
        mean_energy = np.mean(mid_high_band)
        
        # High temporal variation indicates transient events
        if temporal_variation > mean_energy * 0.5:
            return True
        
        return False
    
    def _detect_electrical_hum(self, magnitude: np.ndarray, f: np.ndarray) -> bool:
        """Detect electrical hum at 60Hz and harmonics"""
        
        hum_frequencies = [60, 120, 180, 240]  # 60Hz and harmonics
        hum_detected = False
        
        for hum_freq in hum_frequencies:
            # Find closest frequency bin
            freq_idx = np.argmin(np.abs(f - hum_freq))
            
            if freq_idx < len(magnitude):
                # Check if there's a peak at this frequency
                local_energy = np.mean(magnitude[freq_idx])
                surrounding_energy = np.mean(magnitude[max(0, freq_idx-2):freq_idx+3])
                
                if local_energy > surrounding_energy * 1.5:
                    hum_detected = True
                    break
        
        return hum_detected
    
    def _detect_wind_noise(self, magnitude: np.ndarray, f: np.ndarray) -> bool:
        """Detect wind noise characteristics"""
        
        # Wind noise is typically broadband with emphasis on low frequencies
        low_freq_band = magnitude[f < 1000]
        
        if len(low_freq_band) == 0:
            return False
        
        # Check for broadband characteristics
        energy_variation = np.std(np.mean(low_freq_band, axis=1))
        mean_energy = np.mean(low_freq_band)
        
        # Wind has relatively uniform energy across low frequencies
        if energy_variation < mean_energy * 0.3 and mean_energy > 0.02:
            return True
        
        return False
    
    def _detect_traffic_noise(self, magnitude: np.ndarray, f: np.ndarray) -> bool:
        """Detect traffic noise patterns"""
        
        # Traffic noise has broadband characteristics with rolling patterns
        broadband_energy = np.mean(magnitude, axis=0)
        
        # Look for gradually changing patterns
        if len(broadband_energy) > 5:
            energy_gradient = np.gradient(broadband_energy)
            gradual_changes = np.sum(np.abs(energy_gradient) < np.std(energy_gradient))
            
            # Traffic has gradual energy changes
            if gradual_changes > len(broadband_energy) * 0.7:
                return True
        
        return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics and metrics"""
        
        recent_metrics = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history
        
        if recent_metrics:
            avg_clarity = np.mean([m.clarity_score for m in recent_metrics])
            avg_naturalness = np.mean([m.naturalness_score for m in recent_metrics])
            avg_snr = np.mean([m.signal_to_noise_ratio for m in recent_metrics])
            avg_latency = np.mean([m.latency_ms for m in recent_metrics])
        else:
            avg_clarity = avg_naturalness = avg_snr = avg_latency = 0.0
        
        return {
            "processing_stats": self.processing_stats,
            "current_settings": asdict(self.settings),
            "recent_performance": {
                "average_clarity_score": avg_clarity,
                "average_naturalness_score": avg_naturalness,
                "average_snr": avg_snr,
                "average_latency_ms": avg_latency
            },
            "adaptation_history_size": len(self.adaptation_history),
            "metrics_collected": len(self.metrics_history)
        }
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update processing settings"""
        
        for key, value in new_settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                logger.info(f"Updated audio processing setting: {key} = {value}")
    
    def reset_adaptation(self):
        """Reset adaptive learning models"""
        
        self.adaptation_history.clear()
        self.environment_model = {
            "noise_characteristics": {},
            "room_acoustics": {},
            "user_voice_profile": {}
        }
        logger.info("Reset adaptive audio processing models")