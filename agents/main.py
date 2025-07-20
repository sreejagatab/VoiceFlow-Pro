#!/usr/bin/env python3

import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.plugins import assemblyai, openai, elevenlabs

from voice_agent import VoiceFlowAgent, BusinessLLM

load_dotenv()

logger = logging.getLogger("voiceflow-agent")


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the VoiceFlow Pro agent with real AssemblyAI Universal-Streaming.
    This function is called when a participant joins a LiveKit room.
    """
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"Starting VoiceFlow Pro agent for participant {participant.identity}")

    # Initialize AssemblyAI Universal-Streaming with optimized settings
    stt = assemblyai.STT(
        api_key=os.getenv("ASSEMBLYAI_API_KEY"),
        sample_rate=16000,
        language="en",
        # Universal-Streaming specific optimizations
        speech_model=assemblyai.SpeechModel.UNIVERSAL,
        word_boost=["CRM", "API", "SaaS", "integration", "enterprise", "appointment", 
                   "consultation", "demonstration", "pricing", "subscription"],
        boost_param="high",
        punctuate=True,
        format_text=True,
        disfluencies=False,  # Remove "uh", "um" for cleaner transcripts
    )

    # Initialize Voice Activity Detection
    vad = assemblyai.VAD(
        min_speaking_duration=0.1,  # 100ms minimum speech
        min_silence_duration=0.5,   # 500ms silence before stopping
        max_buffered_speech=30.0,   # Max 30 seconds of buffered speech
    )

    # Initialize business-optimized LLM
    business_llm = BusinessLLM(
        model="gpt-4-turbo-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,  # Lower temperature for more consistent business responses
    )

    # Initialize high-quality TTS
    tts = elevenlabs.TTS(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Professional voice
        model="eleven_turbo_v2",  # Low latency model for real-time
        optimize_streaming_latency=3,  # Optimize for streaming
        stability=0.5,
        similarity_boost=0.75,
    )

    # Create our business agent wrapper
    voiceflow_agent = VoiceFlowAgent(ctx, participant)

    # Set up agent event handlers
    await voiceflow_agent.setup_event_handlers()

    logger.info("VoiceFlow Pro agent fully initialized and running")

    # Keep the connection alive
    await ctx.wait_for_participant()


def prewarm(proc: JobContext):
    """
    Prewarm function to initialize models and services.
    This is called when the worker starts to reduce cold start latency.
    """
    proc.userdata["vad"] = assemblyai.VAD()
    proc.userdata["stt"] = assemblyai.STT()
    proc.userdata["llm"] = openai.LLM()
    proc.userdata["tts"] = elevenlabs.TTS()


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    # Add development mode arguments if not provided
    if len(sys.argv) == 1:
        sys.argv.extend(["dev", "--url", "ws://livekit:7880", "--api-key", "devkey", "--api-secret", "secret"])

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )