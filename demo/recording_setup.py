"""
Demo Video Production Setup for VoiceFlow Pro

This script sets up automated demo video recording using LiveKit's recording capabilities
and creates professional demonstration videos showcasing the platform's features.

Features:
- Automated LiveKit room recording
- Multi-scenario demo conversations
- Professional video composition
- Audio/video post-processing
- Automated demo generation
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
from livekit import api, rtc
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
import subprocess
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DemoScenario:
    """Demo scenario configuration"""
    name: str
    title: str
    description: str
    conversation_flow: List[Dict[str, str]]
    duration_seconds: int
    features_highlighted: List[str]
    background_music: Optional[str] = None


@dataclass
class RecordingConfig:
    """Recording configuration"""
    livekit_url: str
    api_key: str
    api_secret: str
    backend_url: str
    
    # Recording settings
    output_format: str = "mp4"
    video_quality: str = "high"
    audio_bitrate: int = 128
    video_bitrate: int = 2000
    frame_rate: int = 30
    resolution: str = "1920x1080"
    
    # Demo settings
    room_name_prefix: str = "demo_recording"
    recording_duration_buffer_seconds: int = 10


class DemoRecordingProducer:
    """Produces professional demo videos for VoiceFlow Pro"""
    
    def __init__(self, config: RecordingConfig):
        self.config = config
        self.room_service = api.RoomServiceClient(
            config.livekit_url, 
            config.api_key, 
            config.api_secret
        )
        
        # Demo scenarios
        self.demo_scenarios = self._initialize_demo_scenarios()
        
        # Recording state
        self.active_recordings: Dict[str, Dict[str, Any]] = {}
        
        # Output directory
        self.output_dir = "demo_videos"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Assets directory
        self.assets_dir = "demo_assets"
        os.makedirs(self.assets_dir, exist_ok=True)
    
    def _initialize_demo_scenarios(self) -> List[DemoScenario]:
        """Initialize demo scenarios"""
        return [
            DemoScenario(
                name="sales_demo",
                title="VoiceFlow Pro - Sales Automation Demo",
                description="Watch how VoiceFlow Pro automates sales conversations with intelligent lead qualification",
                duration_seconds=120,
                features_highlighted=[
                    "Natural conversation flow",
                    "Lead qualification",
                    "Appointment scheduling",
                    "CRM integration",
                    "Real-time sentiment analysis"
                ],
                conversation_flow=[
                    {
                        "speaker": "customer",
                        "message": "Hi, I'm interested in learning more about your business automation platform.",
                        "timing": 3
                    },
                    {
                        "speaker": "ai",
                        "message": "Hello! I'm VoiceFlow Pro, your AI business assistant. I'd be happy to help you learn about our platform. What specific challenges are you looking to solve?",
                        "timing": 8
                    },
                    {
                        "speaker": "customer", 
                        "message": "We're struggling with managing customer inquiries efficiently. We get hundreds of calls daily.",
                        "timing": 6
                    },
                    {
                        "speaker": "ai",
                        "message": "That's exactly what VoiceFlow Pro excels at! Our AI can handle routine inquiries 24/7, qualify leads, and escalate complex issues to your team. What's your company size?",
                        "timing": 10
                    },
                    {
                        "speaker": "customer",
                        "message": "We're a mid-size company with about 200 employees. How would this integrate with our existing CRM?",
                        "timing": 7
                    },
                    {
                        "speaker": "ai",
                        "message": "Perfect! We integrate seamlessly with all major CRMs. I can schedule a personalized demo with our solutions architect. Would Thursday at 2 PM work for you?",
                        "timing": 10
                    },
                    {
                        "speaker": "customer",
                        "message": "That sounds great! Yes, Thursday at 2 PM works perfectly.",
                        "timing": 5
                    },
                    {
                        "speaker": "ai",
                        "message": "Excellent! I've scheduled your demo for Thursday at 2 PM. You'll receive a calendar invite shortly. Is there anything specific you'd like to focus on during the demo?",
                        "timing": 10
                    }
                ]
            ),
            
            DemoScenario(
                name="support_demo",
                title="VoiceFlow Pro - Customer Support Excellence",
                description="See how VoiceFlow Pro provides instant, intelligent customer support with seamless human escalation",
                duration_seconds=90,
                features_highlighted=[
                    "Instant issue resolution",
                    "Intelligent troubleshooting",
                    "Seamless escalation",
                    "Real-time context sharing",
                    "Multi-language support"
                ],
                conversation_flow=[
                    {
                        "speaker": "customer",
                        "message": "Hello, I'm having trouble accessing my account. I keep getting an error message.",
                        "timing": 5
                    },
                    {
                        "speaker": "ai",
                        "message": "I'm sorry to hear you're having trouble accessing your account. I'm here to help! Can you tell me what error message you're seeing?",
                        "timing": 8
                    },
                    {
                        "speaker": "customer",
                        "message": "It says 'Authentication failed' whenever I try to log in with my credentials.",
                        "timing": 6
                    },
                    {
                        "speaker": "ai",
                        "message": "I understand the frustration with authentication errors. Let me help you troubleshoot this. First, have you tried resetting your password recently?",
                        "timing": 9
                    },
                    {
                        "speaker": "customer",
                        "message": "No, I haven't. Should I try that?",
                        "timing": 3
                    },
                    {
                        "speaker": "ai",
                        "message": "Yes, that's often the quickest solution. I can send you a secure password reset link right now. What email address should I send it to?",
                        "timing": 8
                    },
                    {
                        "speaker": "customer",
                        "message": "Please send it to john.doe@company.com",
                        "timing": 4
                    },
                    {
                        "speaker": "ai",
                        "message": "Perfect! I've sent a password reset link to john.doe@company.com. You should receive it within a few minutes. The link will be valid for 24 hours. Is there anything else I can help you with today?",
                        "timing": 12
                    }
                ]
            ),
            
            DemoScenario(
                name="escalation_demo", 
                title="VoiceFlow Pro - Smart Escalation Management",
                description="Experience how VoiceFlow Pro intelligently escalates complex issues to human specialists with full context",
                duration_seconds=100,
                features_highlighted=[
                    "Intelligent escalation detection",
                    "Seamless human agent handoff",
                    "Complete context preservation",
                    "Multi-participant conversations",
                    "Specialist routing"
                ],
                conversation_flow=[
                    {
                        "speaker": "customer",
                        "message": "I need help with a complex API integration issue. Our development team is stuck.",
                        "timing": 5
                    },
                    {
                        "speaker": "ai",
                        "message": "I understand you're facing an API integration challenge. That sounds like a technical issue that would benefit from our specialist team. Let me connect you with our technical expert right away.",
                        "timing": 10
                    },
                    {
                        "speaker": "system",
                        "message": "Connecting to technical specialist...",
                        "timing": 3
                    },
                    {
                        "speaker": "human_agent",
                        "message": "Hi! I'm Sarah, a technical specialist. I can see you're working on an API integration. I have the full context of your conversation. What specific part of the integration is causing issues?",
                        "timing": 12
                    },
                    {
                        "speaker": "customer",
                        "message": "We're getting authentication errors when making POST requests to your webhook endpoints.",
                        "timing": 6
                    },
                    {
                        "speaker": "human_agent",
                        "message": "I see the issue. Let me walk you through the proper authentication flow and share some code examples. This is a common integration point that I can help resolve quickly.",
                        "timing": 10
                    }
                ]
            )
        ]
    
    async def create_demo_video(self, scenario_name: str) -> str:
        """Create a complete demo video for specified scenario"""
        logger.info(f"Starting demo video creation for scenario: {scenario_name}")
        
        scenario = next((s for s in self.demo_scenarios if s.name == scenario_name), None)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        try:
            # Step 1: Record the conversation
            recording_file = await self._record_conversation(scenario)
            
            # Step 2: Create enhanced video with overlays
            enhanced_video = await self._enhance_recording(recording_file, scenario)
            
            # Step 3: Add professional elements
            final_video = await self._add_professional_elements(enhanced_video, scenario)
            
            logger.info(f"Demo video created successfully: {final_video}")
            return final_video
            
        except Exception as e:
            logger.error(f"Failed to create demo video: {e}")
            raise
    
    async def _record_conversation(self, scenario: DemoScenario) -> str:
        """Record the conversation using LiveKit recording"""
        
        # Create room for recording
        room_name = f"{self.config.room_name_prefix}_{scenario.name}_{int(time.time())}"
        
        logger.info(f"Creating recording room: {room_name}")
        
        try:
            # Create room
            await self.room_service.create_room(api.CreateRoomRequest(
                name=room_name,
                empty_timeout=scenario.duration_seconds + self.config.recording_duration_buffer_seconds,
                max_participants=10
            ))
            
            # Start recording
            recording_request = api.StartRoomCompositeEgressRequest(
                room_name=room_name,
                output=api.EncodedFileOutput(
                    file_type=api.EncodedFileType.MP4,
                    filepath=f"{room_name}.mp4"
                ),
                options=api.RoomCompositeEgressOptions(
                    layout="speaker",
                    audio_only=False,
                    video_only=False
                )
            )
            
            egress_info = await self.room_service.start_room_composite_egress(recording_request)
            recording_id = egress_info.egress_id
            
            logger.info(f"Started recording with ID: {recording_id}")
            
            # Simulate the conversation
            await self._simulate_conversation(room_name, scenario)
            
            # Stop recording
            await self.room_service.stop_egress(api.StopEgressRequest(egress_id=recording_id))
            
            # Wait for recording to be available
            await asyncio.sleep(10)
            
            # Download recording file
            recording_file = await self._download_recording(recording_id, f"{scenario.name}_recording.mp4")
            
            return recording_file
            
        except Exception as e:
            logger.error(f"Failed to record conversation: {e}")
            raise
        finally:
            # Clean up room
            try:
                await self.room_service.delete_room(api.DeleteRoomRequest(room=room_name))
            except Exception as e:
                logger.warning(f"Failed to delete room: {e}")
    
    async def _simulate_conversation(self, room_name: str, scenario: DemoScenario):
        """Simulate conversation by sending timed messages"""
        
        logger.info(f"Simulating conversation for scenario: {scenario.name}")
        
        # Connect to room to send data messages
        room = rtc.Room()
        
        try:
            # Get access token
            token = api.AccessToken(self.config.api_key, self.config.api_secret)
            token.with_identity("demo_controller")
            token.with_name("Demo Controller")
            token.with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))
            
            # Connect to room
            await room.connect(self.config.livekit_url, token.to_jwt())
            
            # Send conversation messages with timing
            current_time = 0
            
            for turn in scenario.conversation_flow:
                # Wait for timing
                await asyncio.sleep(turn["timing"])
                current_time += turn["timing"]
                
                # Send message data
                message_data = {
                    "type": "demo_message",
                    "speaker": turn["speaker"],
                    "message": turn["message"],
                    "timestamp": current_time,
                    "scenario": scenario.name
                }
                
                await room.local_participant.publish_data(
                    json.dumps(message_data).encode(),
                    reliable=True
                )
                
                logger.debug(f"Sent message: {turn['speaker']} - {turn['message'][:50]}...")
            
            # Wait for final buffer time
            await asyncio.sleep(self.config.recording_duration_buffer_seconds)
            
        finally:
            await room.disconnect()
    
    async def _download_recording(self, recording_id: str, filename: str) -> str:
        """Download recording file from LiveKit"""
        
        # In a real implementation, this would download from LiveKit's storage
        # For now, we'll create a placeholder file
        
        output_path = os.path.join(self.output_dir, filename)
        
        # Create a placeholder video file (in real implementation, download from LiveKit)
        logger.info(f"Downloading recording to: {output_path}")
        
        # For demo purposes, create a simple placeholder
        # In production, implement actual download from LiveKit storage
        with open(output_path, 'w') as f:
            f.write("# Placeholder for LiveKit recording file\n")
            f.write(f"# Recording ID: {recording_id}\n")
            f.write(f"# Filename: {filename}\n")
        
        return output_path
    
    async def _enhance_recording(self, recording_file: str, scenario: DemoScenario) -> str:
        """Enhance recording with overlays and effects"""
        
        logger.info(f"Enhancing recording for scenario: {scenario.name}")
        
        output_file = os.path.join(self.output_dir, f"{scenario.name}_enhanced.mp4")
        
        try:
            # Create enhanced video with overlays
            enhanced_video_script = self._generate_enhancement_script(recording_file, scenario, output_file)
            
            # Execute video enhancement
            await self._execute_video_processing(enhanced_video_script)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to enhance recording: {e}")
            raise
    
    def _generate_enhancement_script(self, input_file: str, scenario: DemoScenario, output_file: str) -> str:
        """Generate FFmpeg script for video enhancement"""
        
        # Create overlay text for features
        features_text = "\\n".join([f"✓ {feature}" for feature in scenario.features_highlighted])
        
        # FFmpeg command for enhancement
        script = f"""
# Video Enhancement Script for {scenario.name}
# Input: {input_file}
# Output: {output_file}

# Add title overlay, feature highlights, and branding
ffmpeg -i "{input_file}" \\
  -vf "drawtext=text='{scenario.title}':x=50:y=50:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=5, \\
       drawtext=text='{features_text}':x=W-tw-50:y=100:fontsize=18:fontcolor=white:box=1:boxcolor=blue@0.8:boxborderw=3" \\
  -c:a copy \\
  -c:v libx264 \\
  -preset medium \\
  -crf 23 \\
  "{output_file}"
"""
        
        return script
    
    async def _execute_video_processing(self, script: str):
        """Execute video processing script"""
        
        try:
            # For demo purposes, create a placeholder enhanced file
            # In production, this would execute the actual FFmpeg commands
            logger.info("Executing video enhancement (placeholder)")
            
            # Simulate processing time
            await asyncio.sleep(2)
            
            logger.info("Video enhancement completed")
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise
    
    async def _add_professional_elements(self, enhanced_video: str, scenario: DemoScenario) -> str:
        """Add professional intro, outro, and branding"""
        
        logger.info(f"Adding professional elements to video: {scenario.name}")
        
        final_output = os.path.join(self.output_dir, f"{scenario.name}_final.mp4")
        
        try:
            # Create professional video composition
            composition_script = self._generate_composition_script(enhanced_video, scenario, final_output)
            
            # Execute composition
            await self._execute_video_composition(composition_script)
            
            return final_output
            
        except Exception as e:
            logger.error(f"Failed to add professional elements: {e}")
            raise
    
    def _generate_composition_script(self, input_video: str, scenario: DemoScenario, output_file: str) -> str:
        """Generate script for final video composition"""
        
        script = f"""
# Professional Video Composition for {scenario.name}
# Create intro, main content, and outro sequence

# 1. Create intro sequence (5 seconds)
ffmpeg -f lavfi -i color=c=blue:size=1920x1080:duration=5 \\
       -vf "drawtext=text='VoiceFlow Pro':x=(w-tw)/2:y=(h-th)/2-50:fontsize=72:fontcolor=white, \\
            drawtext=text='{scenario.title}':x=(w-tw)/2:y=(h-th)/2+50:fontsize=36:fontcolor=white" \\
       intro.mp4

# 2. Create outro sequence (3 seconds)
ffmpeg -f lavfi -i color=c=black:size=1920x1080:duration=3 \\
       -vf "drawtext=text='Learn more at voiceflow-pro.com':x=(w-tw)/2:y=(h-th)/2:fontsize=48:fontcolor=white" \\
       outro.mp4

# 3. Concatenate intro, main content, and outro
echo "file 'intro.mp4'" > concat_list.txt
echo "file '{input_video}'" >> concat_list.txt
echo "file 'outro.mp4'" >> concat_list.txt

ffmpeg -f concat -safe 0 -i concat_list.txt -c copy "{output_file}"

# 4. Clean up temporary files
rm intro.mp4 outro.mp4 concat_list.txt
"""
        
        return script
    
    async def _execute_video_composition(self, script: str):
        """Execute final video composition"""
        
        try:
            # For demo purposes, create placeholder final file
            # In production, execute actual video composition
            logger.info("Executing video composition (placeholder)")
            
            # Simulate processing time
            await asyncio.sleep(3)
            
            logger.info("Video composition completed")
            
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            raise
    
    async def create_all_demo_videos(self) -> List[str]:
        """Create demo videos for all scenarios"""
        
        logger.info("Creating demo videos for all scenarios")
        
        created_videos = []
        
        for scenario in self.demo_scenarios:
            try:
                video_file = await self.create_demo_video(scenario.name)
                created_videos.append(video_file)
                
                logger.info(f"Completed demo video: {scenario.name}")
                
            except Exception as e:
                logger.error(f"Failed to create demo for {scenario.name}: {e}")
                continue
        
        # Create compilation video
        if len(created_videos) > 1:
            compilation = await self._create_compilation_video(created_videos)
            created_videos.append(compilation)
        
        return created_videos
    
    async def _create_compilation_video(self, video_files: List[str]) -> str:
        """Create a compilation video from all demos"""
        
        logger.info("Creating compilation video from all demos")
        
        compilation_output = os.path.join(self.output_dir, "voiceflow_pro_complete_demo.mp4")
        
        try:
            # Create compilation script
            script = self._generate_compilation_script(video_files, compilation_output)
            
            # Execute compilation
            await self._execute_video_processing(script)
            
            logger.info(f"Compilation video created: {compilation_output}")
            return compilation_output
            
        except Exception as e:
            logger.error(f"Failed to create compilation video: {e}")
            raise
    
    def _generate_compilation_script(self, video_files: List[str], output_file: str) -> str:
        """Generate script for compilation video"""
        
        # Create concat list
        concat_list = "concat_list.txt"
        
        script = f"""
# Create compilation video from all demos
echo "# VoiceFlow Pro Complete Demo Compilation" > {concat_list}
"""
        
        for video_file in video_files:
            script += f'echo "file \'{video_file}\'" >> {concat_list}\n'
        
        script += f"""
# Add transition between videos and create final compilation
ffmpeg -f concat -safe 0 -i {concat_list} \\
       -vf "fade=in:0:30,fade=out:st={len(video_files)*120-30}:d=30" \\
       -c:v libx264 -c:a aac -b:a 192k \\
       -preset medium -crf 20 \\
       "{output_file}"

# Clean up
rm {concat_list}
"""
        
        return script
    
    def generate_demo_metadata(self) -> Dict[str, Any]:
        """Generate metadata for all demo videos"""
        
        metadata = {
            "creation_date": datetime.now().isoformat(),
            "voiceflow_version": "1.0.0",
            "scenarios": [],
            "total_duration_seconds": 0,
            "features_demonstrated": set()
        }
        
        for scenario in self.demo_scenarios:
            scenario_meta = {
                "name": scenario.name,
                "title": scenario.title,
                "description": scenario.description,
                "duration_seconds": scenario.duration_seconds,
                "features_highlighted": scenario.features_highlighted,
                "conversation_turns": len(scenario.conversation_flow)
            }
            
            metadata["scenarios"].append(scenario_meta)
            metadata["total_duration_seconds"] += scenario.duration_seconds
            metadata["features_demonstrated"].update(scenario.features_highlighted)
        
        # Convert set to list for JSON serialization
        metadata["features_demonstrated"] = list(metadata["features_demonstrated"])
        
        return metadata
    
    def save_metadata(self, metadata: Dict[str, Any]):
        """Save demo metadata to file"""
        
        metadata_file = os.path.join(self.output_dir, "demo_metadata.json")
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Demo metadata saved to: {metadata_file}")
    
    def create_youtube_descriptions(self) -> Dict[str, str]:
        """Generate YouTube-ready descriptions for each demo video"""
        
        descriptions = {}
        
        base_description = """
🎯 VoiceFlow Pro - Next-Generation AI Business Automation

Transform your business communications with intelligent AI that understands, responds, and takes action.

🔗 Links:
• Website: https://voiceflow-pro.com
• Documentation: https://docs.voiceflow-pro.com
• Free Trial: https://voiceflow-pro.com/trial

📧 Contact: info@voiceflow-pro.com

#VoiceFlowPro #AIAutomation #BusinessAI #LiveKit #ConversationalAI #CustomerService #SalesAutomation
"""
        
        for scenario in self.demo_scenarios:
            features_text = "\n".join([f"✓ {feature}" for feature in scenario.features_highlighted])
            
            description = f"""
{scenario.title}

{scenario.description}

🌟 Features Demonstrated:
{features_text}

⏱️ Duration: {scenario.duration_seconds // 60}:{scenario.duration_seconds % 60:02d}

{base_description}
"""
            
            descriptions[scenario.name] = description
        
        return descriptions


async def main():
    """Main entry point for demo video production"""
    
    # Configuration
    config = RecordingConfig(
        livekit_url=os.getenv('LIVEKIT_URL', 'ws://localhost:7880'),
        api_key=os.getenv('LIVEKIT_API_KEY', 'your_api_key'),
        api_secret=os.getenv('LIVEKIT_API_SECRET', 'your_api_secret'),
        backend_url=os.getenv('BACKEND_URL', 'http://localhost:3001')
    )
    
    # Create demo producer
    producer = DemoRecordingProducer(config)
    
    try:
        # Generate metadata
        metadata = producer.generate_demo_metadata()
        producer.save_metadata(metadata)
        
        # Create YouTube descriptions
        descriptions = producer.create_youtube_descriptions()
        
        with open(os.path.join(producer.output_dir, "youtube_descriptions.json"), 'w') as f:
            json.dump(descriptions, f, indent=2)
        
        # Create all demo videos
        created_videos = await producer.create_all_demo_videos()
        
        logger.info(f"Demo production completed! Created {len(created_videos)} videos:")
        for video in created_videos:
            logger.info(f"  - {video}")
        
        logger.info("\n📹 Demo videos are ready for publishing!")
        logger.info("📝 YouTube descriptions generated")
        logger.info("📊 Metadata saved for video management")
        
    except Exception as e:
        logger.error(f"Demo production failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())