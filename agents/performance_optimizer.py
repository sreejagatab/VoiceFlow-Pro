"""
Performance Optimization and Audio Quality Tuning for VoiceFlow Pro

This module provides advanced performance optimization including:
- Audio quality enhancement and tuning
- Latency optimization for sub-400ms targets
- Real-time performance monitoring
- Adaptive quality adjustment
- Resource management and optimization
"""

import asyncio
import logging
import time
import psutil
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
from livekit import rtc
from livekit.agents import llm

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Performance optimization levels"""
    ULTRA_LOW_LATENCY = "ultra_low_latency"  # < 300ms
    LOW_LATENCY = "low_latency"              # < 500ms
    BALANCED = "balanced"                     # < 800ms
    HIGH_QUALITY = "high_quality"           # Focus on quality over speed


class AudioQuality(Enum):
    """Audio quality levels"""
    STUDIO = "studio"        # 48kHz, highest quality
    HIGH = "high"           # 24kHz, high quality
    STANDARD = "standard"   # 16kHz, standard quality
    EFFICIENT = "efficient" # 8kHz, optimized for speed


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    # Latency metrics (milliseconds)
    stt_latency: float
    llm_latency: float
    tts_latency: float
    total_latency: float
    
    # Audio metrics
    audio_quality_score: float
    noise_level: float
    signal_strength: float
    packet_loss: float
    
    # System metrics
    cpu_usage: float
    memory_usage: float
    network_latency: float
    
    # Processing metrics
    processing_queue_size: int
    concurrent_sessions: int
    
    # Quality metrics
    transcription_accuracy: float
    response_relevance: float
    voice_clarity: float
    
    # Timestamp
    measured_at: datetime


@dataclass
class OptimizationSettings:
    """Optimization configuration settings"""
    # Audio settings
    sample_rate: int
    bit_depth: int
    channels: int
    
    # Processing settings
    chunk_size: int
    buffer_size: int
    processing_threads: int
    
    # Quality settings
    noise_suppression: bool
    echo_cancellation: bool
    auto_gain_control: bool
    
    # Latency settings
    streaming_enabled: bool
    partial_results: bool
    interrupt_threshold: float
    
    # Model settings
    stt_model: str
    llm_model: str
    tts_model: str


class PerformanceOptimizer:
    """
    Advanced performance optimization and audio quality tuning
    """
    
    def __init__(self):
        # Current optimization settings
        self.current_settings = OptimizationSettings(
            sample_rate=16000,
            bit_depth=16,
            channels=1,
            chunk_size=1024,
            buffer_size=4096,
            processing_threads=4,
            noise_suppression=True,
            echo_cancellation=True,
            auto_gain_control=True,
            streaming_enabled=True,
            partial_results=True,
            interrupt_threshold=0.5,
            stt_model="universal",
            llm_model="gpt-4-turbo-preview",
            tts_model="eleven_turbo_v2"
        )
        
        # Performance targets
        self.performance_targets = {
            OptimizationLevel.ULTRA_LOW_LATENCY: {
                "total_latency": 300,
                "stt_latency": 100,
                "llm_latency": 150,
                "tts_latency": 50
            },
            OptimizationLevel.LOW_LATENCY: {
                "total_latency": 500,
                "stt_latency": 150,
                "llm_latency": 250,
                "tts_latency": 100
            },
            OptimizationLevel.BALANCED: {
                "total_latency": 800,
                "stt_latency": 200,
                "llm_latency": 400,
                "tts_latency": 200
            }
        }
        
        # Audio quality presets
        self.audio_presets = {
            AudioQuality.STUDIO: {
                "sample_rate": 48000,
                "bit_depth": 24,
                "noise_suppression": True,
                "processing_complexity": "high"
            },
            AudioQuality.HIGH: {
                "sample_rate": 24000,
                "bit_depth": 16,
                "noise_suppression": True,
                "processing_complexity": "medium"
            },
            AudioQuality.STANDARD: {
                "sample_rate": 16000,
                "bit_depth": 16,
                "noise_suppression": True,
                "processing_complexity": "low"
            },
            AudioQuality.EFFICIENT: {
                "sample_rate": 8000,
                "bit_depth": 16,
                "noise_suppression": False,
                "processing_complexity": "minimal"
            }
        }
        
        # Performance monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.optimization_level = OptimizationLevel.LOW_LATENCY
        self.audio_quality = AudioQuality.STANDARD
        
        # Adaptive optimization state
        self.adaptive_enabled = True
        self.last_optimization = datetime.now()
        self.optimization_cooldown = timedelta(seconds=30)
        
        # Performance thresholds for adaptive optimization
        self.performance_thresholds = {
            "latency_warning": 600,     # ms
            "latency_critical": 1000,   # ms
            "cpu_warning": 80,          # %
            "memory_warning": 85,       # %
            "quality_minimum": 0.7      # quality score
        }
    
    async def measure_performance_metrics(self, room: rtc.Room,
                                        session_context: Dict[str, Any]) -> PerformanceMetrics:
        """
        Measure comprehensive performance metrics
        """
        start_time = time.time()
        
        # Measure STT latency (simulate with actual measurement points)
        stt_start = time.time()
        await asyncio.sleep(0.05)  # Simulate STT processing
        stt_latency = (time.time() - stt_start) * 1000
        
        # Measure LLM latency
        llm_start = time.time()
        await asyncio.sleep(0.15)  # Simulate LLM processing
        llm_latency = (time.time() - llm_start) * 1000
        
        # Measure TTS latency
        tts_start = time.time()
        await asyncio.sleep(0.08)  # Simulate TTS processing
        tts_latency = (time.time() - tts_start) * 1000
        
        total_latency = (time.time() - start_time) * 1000
        
        # Audio quality metrics
        audio_metrics = await self._analyze_audio_quality(room)
        
        # System metrics
        system_metrics = self._get_system_metrics()
        
        # Processing metrics
        processing_metrics = self._get_processing_metrics(session_context)
        
        metrics = PerformanceMetrics(
            stt_latency=stt_latency,
            llm_latency=llm_latency,
            tts_latency=tts_latency,
            total_latency=total_latency,
            audio_quality_score=audio_metrics["quality_score"],
            noise_level=audio_metrics["noise_level"],
            signal_strength=audio_metrics["signal_strength"],
            packet_loss=audio_metrics["packet_loss"],
            cpu_usage=system_metrics["cpu_usage"],
            memory_usage=system_metrics["memory_usage"],
            network_latency=system_metrics["network_latency"],
            processing_queue_size=processing_metrics["queue_size"],
            concurrent_sessions=processing_metrics["concurrent_sessions"],
            transcription_accuracy=0.95,  # Would be measured from actual STT
            response_relevance=0.88,      # Would be measured from LLM quality
            voice_clarity=audio_metrics["clarity"],
            measured_at=datetime.now()
        )
        
        # Store metrics history
        self.metrics_history.append(metrics)
        
        # Keep only last 100 measurements
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return metrics
    
    async def _analyze_audio_quality(self, room: rtc.Room) -> Dict[str, float]:
        """Analyze real-time audio quality metrics"""
        
        # In production, this would analyze actual audio streams
        # For now, simulate realistic metrics
        
        quality_metrics = {
            "quality_score": np.random.normal(0.85, 0.1),  # 85% ± 10%
            "noise_level": np.random.exponential(0.1),     # Low noise level
            "signal_strength": np.random.normal(0.9, 0.05), # Strong signal
            "packet_loss": np.random.exponential(0.01),    # Very low packet loss
            "clarity": np.random.normal(0.88, 0.08)        # Good clarity
        }
        
        # Clamp values to reasonable ranges
        for key, value in quality_metrics.items():
            quality_metrics[key] = max(0.0, min(1.0, value))
        
        return quality_metrics
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get system resource metrics"""
        
        return {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "network_latency": np.random.normal(50, 10)  # Simulate network latency
        }
    
    def _get_processing_metrics(self, session_context: Dict[str, Any]) -> Dict[str, int]:
        """Get processing queue and session metrics"""
        
        return {
            "queue_size": session_context.get("queue_size", 0),
            "concurrent_sessions": session_context.get("concurrent_sessions", 1)
        }
    
    async def optimize_for_target(self, target_level: OptimizationLevel,
                                audio_quality: AudioQuality = None) -> OptimizationSettings:
        """
        Optimize settings for specific performance target
        """
        logger.info(f"Optimizing for {target_level.value} performance")
        
        # Get target metrics
        targets = self.performance_targets[target_level]
        
        # Update optimization level
        self.optimization_level = target_level
        if audio_quality:
            self.audio_quality = audio_quality
        
        # Create optimized settings
        optimized_settings = OptimizationSettings(
            sample_rate=self.audio_presets[self.audio_quality]["sample_rate"],
            bit_depth=self.audio_presets[self.audio_quality]["bit_depth"],
            channels=1,  # Mono for voice
            chunk_size=self._calculate_optimal_chunk_size(target_level),
            buffer_size=self._calculate_optimal_buffer_size(target_level),
            processing_threads=self._calculate_optimal_threads(target_level),
            noise_suppression=self.audio_presets[self.audio_quality]["noise_suppression"],
            echo_cancellation=True,
            auto_gain_control=True,
            streaming_enabled=target_level in [OptimizationLevel.ULTRA_LOW_LATENCY, OptimizationLevel.LOW_LATENCY],
            partial_results=target_level != OptimizationLevel.HIGH_QUALITY,
            interrupt_threshold=self._calculate_interrupt_threshold(target_level),
            stt_model=self._select_stt_model(target_level),
            llm_model=self._select_llm_model(target_level),
            tts_model=self._select_tts_model(target_level)
        )
        
        # Apply settings
        self.current_settings = optimized_settings
        await self._apply_optimization_settings(optimized_settings)
        
        return optimized_settings
    
    def _calculate_optimal_chunk_size(self, target_level: OptimizationLevel) -> int:
        """Calculate optimal audio chunk size for latency target"""
        
        chunk_sizes = {
            OptimizationLevel.ULTRA_LOW_LATENCY: 512,   # Smallest chunks for lowest latency
            OptimizationLevel.LOW_LATENCY: 1024,        # Small chunks
            OptimizationLevel.BALANCED: 2048,           # Medium chunks
            OptimizationLevel.HIGH_QUALITY: 4096       # Large chunks for quality
        }
        
        return chunk_sizes[target_level]
    
    def _calculate_optimal_buffer_size(self, target_level: OptimizationLevel) -> int:
        """Calculate optimal buffer size"""
        
        buffer_sizes = {
            OptimizationLevel.ULTRA_LOW_LATENCY: 2048,
            OptimizationLevel.LOW_LATENCY: 4096,
            OptimizationLevel.BALANCED: 8192,
            OptimizationLevel.HIGH_QUALITY: 16384
        }
        
        return buffer_sizes[target_level]
    
    def _calculate_optimal_threads(self, target_level: OptimizationLevel) -> int:
        """Calculate optimal number of processing threads"""
        
        cpu_count = psutil.cpu_count()
        
        thread_ratios = {
            OptimizationLevel.ULTRA_LOW_LATENCY: 0.8,   # Use most CPUs
            OptimizationLevel.LOW_LATENCY: 0.6,
            OptimizationLevel.BALANCED: 0.5,
            OptimizationLevel.HIGH_QUALITY: 0.4        # Leave room for quality processing
        }
        
        return max(2, int(cpu_count * thread_ratios[target_level]))
    
    def _calculate_interrupt_threshold(self, target_level: OptimizationLevel) -> float:
        """Calculate optimal interrupt threshold for voice activity"""
        
        thresholds = {
            OptimizationLevel.ULTRA_LOW_LATENCY: 0.3,   # Very sensitive
            OptimizationLevel.LOW_LATENCY: 0.5,         # Sensitive
            OptimizationLevel.BALANCED: 0.7,            # Balanced
            OptimizationLevel.HIGH_QUALITY: 0.8        # Conservative
        }
        
        return thresholds[target_level]
    
    def _select_stt_model(self, target_level: OptimizationLevel) -> str:
        """Select optimal STT model for target"""
        
        models = {
            OptimizationLevel.ULTRA_LOW_LATENCY: "universal_streaming",
            OptimizationLevel.LOW_LATENCY: "universal_streaming",
            OptimizationLevel.BALANCED: "universal",
            OptimizationLevel.HIGH_QUALITY: "universal_enhanced"
        }
        
        return models[target_level]
    
    def _select_llm_model(self, target_level: OptimizationLevel) -> str:
        """Select optimal LLM model for target"""
        
        models = {
            OptimizationLevel.ULTRA_LOW_LATENCY: "gpt-3.5-turbo",
            OptimizationLevel.LOW_LATENCY: "gpt-3.5-turbo",
            OptimizationLevel.BALANCED: "gpt-4-turbo-preview",
            OptimizationLevel.HIGH_QUALITY: "gpt-4-turbo-preview"
        }
        
        return models[target_level]
    
    def _select_tts_model(self, target_level: OptimizationLevel) -> str:
        """Select optimal TTS model for target"""
        
        models = {
            OptimizationLevel.ULTRA_LOW_LATENCY: "eleven_turbo_v2",
            OptimizationLevel.LOW_LATENCY: "eleven_turbo_v2",
            OptimizationLevel.BALANCED: "eleven_multilingual_v2",
            OptimizationLevel.HIGH_QUALITY: "eleven_monolingual_v1"
        }
        
        return models[target_level]
    
    async def _apply_optimization_settings(self, settings: OptimizationSettings):
        """Apply optimization settings to the system"""
        
        # In production, this would configure:
        # - Audio processing parameters
        # - Model selection
        # - Buffer sizes
        # - Threading configuration
        
        logger.info(f"Applied optimization settings:")
        logger.info(f"  Sample rate: {settings.sample_rate}Hz")
        logger.info(f"  Chunk size: {settings.chunk_size}")
        logger.info(f"  Processing threads: {settings.processing_threads}")
        logger.info(f"  STT model: {settings.stt_model}")
        logger.info(f"  LLM model: {settings.llm_model}")
        logger.info(f"  TTS model: {settings.tts_model}")
    
    async def adaptive_optimization(self, current_metrics: PerformanceMetrics) -> bool:
        """
        Perform adaptive optimization based on current performance
        """
        if not self.adaptive_enabled:
            return False
        
        # Check if enough time has passed since last optimization
        if datetime.now() - self.last_optimization < self.optimization_cooldown:
            return False
        
        optimization_needed = False
        new_level = self.optimization_level
        
        # Check latency performance
        if current_metrics.total_latency > self.performance_thresholds["latency_critical"]:
            # Critical latency - optimize aggressively
            new_level = OptimizationLevel.ULTRA_LOW_LATENCY
            optimization_needed = True
            logger.warning(f"Critical latency detected: {current_metrics.total_latency}ms")
            
        elif current_metrics.total_latency > self.performance_thresholds["latency_warning"]:
            # Warning latency - moderate optimization
            if self.optimization_level not in [OptimizationLevel.ULTRA_LOW_LATENCY, OptimizationLevel.LOW_LATENCY]:
                new_level = OptimizationLevel.LOW_LATENCY
                optimization_needed = True
                logger.warning(f"High latency detected: {current_metrics.total_latency}ms")
        
        # Check system resources
        if (current_metrics.cpu_usage > self.performance_thresholds["cpu_warning"] or
            current_metrics.memory_usage > self.performance_thresholds["memory_warning"]):
            # High resource usage - reduce processing load
            if self.optimization_level == OptimizationLevel.HIGH_QUALITY:
                new_level = OptimizationLevel.BALANCED
                optimization_needed = True
                logger.warning(f"High resource usage: CPU {current_metrics.cpu_usage}%, Memory {current_metrics.memory_usage}%")
        
        # Check audio quality
        if current_metrics.audio_quality_score < self.performance_thresholds["quality_minimum"]:
            # Poor quality - try to improve
            if self.optimization_level == OptimizationLevel.ULTRA_LOW_LATENCY:
                new_level = OptimizationLevel.LOW_LATENCY
                optimization_needed = True
                logger.warning(f"Poor audio quality: {current_metrics.audio_quality_score:.2f}")
        
        # Apply optimization if needed
        if optimization_needed and new_level != self.optimization_level:
            await self.optimize_for_target(new_level)
            self.last_optimization = datetime.now()
            logger.info(f"Adaptive optimization applied: {self.optimization_level.value} -> {new_level.value}")
            return True
        
        return False
    
    def analyze_performance_trends(self, window_minutes: int = 10) -> Dict[str, Any]:
        """
        Analyze performance trends over specified time window
        """
        if len(self.metrics_history) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Filter metrics within time window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [m for m in self.metrics_history if m.measured_at >= cutoff_time]
        
        if len(recent_metrics) < 2:
            return {"error": "Insufficient recent data"}
        
        # Calculate trends
        latencies = [m.total_latency for m in recent_metrics]
        cpu_usages = [m.cpu_usage for m in recent_metrics]
        quality_scores = [m.audio_quality_score for m in recent_metrics]
        
        trends = {
            "latency": {
                "current": latencies[-1],
                "average": np.mean(latencies),
                "trend": "improving" if latencies[-1] < np.mean(latencies) else "degrading",
                "variance": np.var(latencies)
            },
            "cpu_usage": {
                "current": cpu_usages[-1],
                "average": np.mean(cpu_usages),
                "trend": "improving" if cpu_usages[-1] < np.mean(cpu_usages) else "degrading",
                "peak": max(cpu_usages)
            },
            "audio_quality": {
                "current": quality_scores[-1],
                "average": np.mean(quality_scores),
                "trend": "improving" if quality_scores[-1] > np.mean(quality_scores) else "degrading",
                "minimum": min(quality_scores)
            },
            "analysis_window": f"{window_minutes} minutes",
            "data_points": len(recent_metrics),
            "timestamp": datetime.now().isoformat()
        }
        
        return trends
    
    def get_optimization_recommendations(self, current_metrics: PerformanceMetrics) -> List[str]:
        """
        Get specific optimization recommendations based on current performance
        """
        recommendations = []
        
        # Latency recommendations
        if current_metrics.total_latency > 800:
            recommendations.extend([
                "Enable streaming mode for faster response",
                "Reduce chunk size for lower buffering latency",
                "Consider switching to faster LLM model",
                "Optimize network connection"
            ])
        
        # Audio quality recommendations
        if current_metrics.audio_quality_score < 0.7:
            recommendations.extend([
                "Enable noise suppression",
                "Increase sample rate if bandwidth allows",
                "Check microphone positioning and quality",
                "Reduce background noise in environment"
            ])
        
        # System resource recommendations
        if current_metrics.cpu_usage > 80:
            recommendations.extend([
                "Reduce processing threads",
                "Lower audio sample rate",
                "Close unnecessary applications",
                "Consider upgrading hardware"
            ])
        
        if current_metrics.memory_usage > 85:
            recommendations.extend([
                "Reduce buffer sizes",
                "Clear conversation history cache",
                "Restart application to free memory",
                "Consider adding more RAM"
            ])
        
        # Network recommendations
        if current_metrics.packet_loss > 0.05:  # 5%
            recommendations.extend([
                "Check network connection stability",
                "Consider wired connection over WiFi",
                "Reduce concurrent network usage",
                "Contact ISP if issues persist"
            ])
        
        return recommendations
    
    async def benchmark_performance(self, test_duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Run performance benchmark test
        """
        logger.info(f"Starting performance benchmark for {test_duration_seconds} seconds")
        
        benchmark_start = datetime.now()
        test_metrics = []
        
        # Run benchmark for specified duration
        while (datetime.now() - benchmark_start).total_seconds() < test_duration_seconds:
            # Simulate performance measurement
            metrics = await self.measure_performance_metrics(None, {"benchmark": True})
            test_metrics.append(metrics)
            
            await asyncio.sleep(1)  # Measure every second
        
        # Analyze benchmark results
        latencies = [m.total_latency for m in test_metrics]
        cpu_usages = [m.cpu_usage for m in test_metrics]
        quality_scores = [m.audio_quality_score for m in test_metrics]
        
        benchmark_results = {
            "test_duration": test_duration_seconds,
            "measurements": len(test_metrics),
            "latency": {
                "average": np.mean(latencies),
                "minimum": min(latencies),
                "maximum": max(latencies),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
                "target_met": np.mean(latencies) < self.performance_targets[self.optimization_level]["total_latency"]
            },
            "cpu_usage": {
                "average": np.mean(cpu_usages),
                "peak": max(cpu_usages),
                "stable": np.std(cpu_usages) < 10  # Less than 10% variation
            },
            "audio_quality": {
                "average": np.mean(quality_scores),
                "minimum": min(quality_scores),
                "consistent": np.std(quality_scores) < 0.1  # Less than 10% variation
            },
            "optimization_level": self.optimization_level.value,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Benchmark completed: Avg latency {benchmark_results['latency']['average']:.1f}ms")
        
        return benchmark_results
    
    def export_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Export comprehensive performance report
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.measured_at >= cutoff_time]
        
        if not recent_metrics:
            return {"error": "No data available for specified time period"}
        
        # Calculate comprehensive statistics
        latencies = [m.total_latency for m in recent_metrics]
        stt_latencies = [m.stt_latency for m in recent_metrics]
        llm_latencies = [m.llm_latency for m in recent_metrics]
        tts_latencies = [m.tts_latency for m in recent_metrics]
        
        report = {
            "report_period": f"{hours} hours",
            "data_points": len(recent_metrics),
            "current_optimization": self.optimization_level.value,
            "current_audio_quality": self.audio_quality.value,
            
            "latency_breakdown": {
                "total": {
                    "average": np.mean(latencies),
                    "p95": np.percentile(latencies, 95),
                    "target": self.performance_targets[self.optimization_level]["total_latency"],
                    "target_met_percentage": sum(1 for l in latencies if l < self.performance_targets[self.optimization_level]["total_latency"]) / len(latencies) * 100
                },
                "stt": {"average": np.mean(stt_latencies), "p95": np.percentile(stt_latencies, 95)},
                "llm": {"average": np.mean(llm_latencies), "p95": np.percentile(llm_latencies, 95)},
                "tts": {"average": np.mean(tts_latencies), "p95": np.percentile(tts_latencies, 95)}
            },
            
            "quality_metrics": {
                "audio_quality": {
                    "average": np.mean([m.audio_quality_score for m in recent_metrics]),
                    "minimum": min([m.audio_quality_score for m in recent_metrics])
                },
                "transcription_accuracy": {
                    "average": np.mean([m.transcription_accuracy for m in recent_metrics])
                },
                "voice_clarity": {
                    "average": np.mean([m.voice_clarity for m in recent_metrics])
                }
            },
            
            "system_performance": {
                "cpu_usage": {
                    "average": np.mean([m.cpu_usage for m in recent_metrics]),
                    "peak": max([m.cpu_usage for m in recent_metrics])
                },
                "memory_usage": {
                    "average": np.mean([m.memory_usage for m in recent_metrics]),
                    "peak": max([m.memory_usage for m in recent_metrics])
                }
            },
            
            "generated_at": datetime.now().isoformat()
        }
        
        return report