"""
Dynamic Response Generation with Voice Cloning for VoiceFlow Pro

This module provides advanced response generation that:
- Adapts responses based on customer context and sentiment
- Generates contextually appropriate voice characteristics
- Supports voice cloning for personalized experiences
- Optimizes responses for different business scenarios
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import openai
from elevenlabs import Voice, VoiceSettings, clone, generate, save
from elevenlabs.client import ElevenLabs
import aiohttp
import tempfile

from context_manager import AdvancedContextManager, ContextualMemory
from sentiment_analyzer import AdvancedSentimentAnalyzer, SentimentAnalysis, EmotionalState
from voice_agent import Scenario, Priority, CustomerContext

logger = logging.getLogger(__name__)


class VoiceProfile(Enum):
    """Voice profiles for different business scenarios"""
    PROFESSIONAL_MALE = "professional_male"
    PROFESSIONAL_FEMALE = "professional_female"
    FRIENDLY_MALE = "friendly_male"
    FRIENDLY_FEMALE = "friendly_female"
    TECHNICAL_EXPERT = "technical_expert"
    SALES_SPECIALIST = "sales_specialist"
    SUPPORT_AGENT = "support_agent"
    EXECUTIVE = "executive"


class ResponseStyle(Enum):
    """Response style variations"""
    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    EMPATHETIC = "empathetic"
    TECHNICAL = "technical"
    PERSUASIVE = "persuasive"
    APOLOGETIC = "apologetic"
    ENTHUSIASTIC = "enthusiastic"
    REASSURING = "reassuring"


@dataclass
class VoiceCharacteristics:
    """Voice characteristics for dynamic generation"""
    # ElevenLabs voice settings
    stability: float  # 0.0 to 1.0
    similarity_boost: float  # 0.0 to 1.0
    style: float  # 0.0 to 1.0
    use_speaker_boost: bool
    
    # Speaking characteristics
    speaking_rate: float  # 0.5 to 2.0 (1.0 = normal)
    pitch_variation: float  # 0.0 to 1.0
    emphasis_strength: float  # 0.0 to 1.0
    
    # Personality traits
    formality_level: float  # 0.0 to 1.0
    enthusiasm_level: float  # 0.0 to 1.0
    empathy_level: float  # 0.0 to 1.0
    confidence_level: float  # 0.0 to 1.0


@dataclass
class GeneratedResponse:
    """Complete generated response with audio"""
    text_response: str
    voice_characteristics: VoiceCharacteristics
    audio_url: Optional[str]
    audio_duration_ms: int
    generation_time_ms: float
    confidence_score: float
    response_style: ResponseStyle
    adaptations_made: List[str]
    generated_at: datetime


class DynamicResponseGenerator:
    """
    Advanced response generator with voice cloning and dynamic adaptation
    """
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI()
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        
        # Voice profiles mapping
        self.voice_profiles = {
            VoiceProfile.PROFESSIONAL_FEMALE: {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel - professional
                "characteristics": VoiceCharacteristics(
                    stability=0.7, similarity_boost=0.8, style=0.3, use_speaker_boost=True,
                    speaking_rate=1.0, pitch_variation=0.4, emphasis_strength=0.5,
                    formality_level=0.8, enthusiasm_level=0.5, empathy_level=0.7, confidence_level=0.8
                )
            },
            VoiceProfile.FRIENDLY_MALE: {
                "voice_id": "29vD33N1CtxCmqQRPOHJ",  # Drew - friendly
                "characteristics": VoiceCharacteristics(
                    stability=0.6, similarity_boost=0.7, style=0.5, use_speaker_boost=True,
                    speaking_rate=1.1, pitch_variation=0.6, emphasis_strength=0.6,
                    formality_level=0.4, enthusiasm_level=0.8, empathy_level=0.8, confidence_level=0.7
                )
            },
            VoiceProfile.TECHNICAL_EXPERT: {
                "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - technical
                "characteristics": VoiceCharacteristics(
                    stability=0.8, similarity_boost=0.9, style=0.2, use_speaker_boost=False,
                    speaking_rate=0.9, pitch_variation=0.3, emphasis_strength=0.4,
                    formality_level=0.9, enthusiasm_level=0.3, empathy_level=0.5, confidence_level=0.9
                )
            },
            VoiceProfile.SALES_SPECIALIST: {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Bella - persuasive
                "characteristics": VoiceCharacteristics(
                    stability=0.5, similarity_boost=0.8, style=0.7, use_speaker_boost=True,
                    speaking_rate=1.2, pitch_variation=0.7, emphasis_strength=0.8,
                    formality_level=0.6, enthusiasm_level=0.9, empathy_level=0.6, confidence_level=0.9
                )
            }
        }
        
        # Response templates for different scenarios
        self.response_templates = {
            Scenario.ONBOARDING: {
                ResponseStyle.CONVERSATIONAL: [
                    "Hello {name}! I'm {agent_name}, and I'm here to help make your experience with us exceptional. {context_reference} What brings you here today?",
                    "Welcome to VoiceFlow Pro! I'm excited to learn about your business needs. {context_reference} How can I best assist you?",
                    "Hi there! I'm {agent_name}, your dedicated business automation specialist. {context_reference} What would you like to accomplish today?"
                ]
            },
            Scenario.SALES: {
                ResponseStyle.PERSUASIVE: [
                    "I understand you're evaluating solutions for {pain_point}. Based on companies similar to yours, I've seen {success_metric} improvements. Let me show you how we can achieve that for {company}.",
                    "That's exactly the challenge our platform was designed to solve. {social_proof} Would you like to see a customized demo for {company}?",
                    "Perfect! You're not alone in facing {challenge}. {success_story} I'd love to explore how we can deliver similar results for you."
                ]
            },
            Scenario.SUPPORT: {
                ResponseStyle.EMPATHETIC: [
                    "I completely understand how frustrating that must be, {name}. {acknowledgment} Let me get this resolved for you right away.",
                    "I'm really sorry you're experiencing this issue. {context_reference} I'm going to make sure we get this sorted out immediately.",
                    "That sounds incredibly frustrating, and I appreciate you bringing this to our attention. {empathy_statement} Let's fix this together."
                ]
            },
            Scenario.ESCALATION: {
                ResponseStyle.APOLOGETIC: [
                    "I sincerely apologize for the situation you've experienced, {name}. {acknowledgment} I'm immediately connecting you with my supervisor who will have full context.",
                    "I'm truly sorry this has reached this point. {summary} Let me get you to the right person who can resolve this immediately.",
                    "You're absolutely right to escalate this, {name}. {accountability} I'm bringing in additional resources to ensure this gets resolved properly."
                ]
            }
        }
        
        # Context manager and sentiment analyzer
        self.context_manager = AdvancedContextManager()
        self.sentiment_analyzer = AdvancedSentimentAnalyzer()
        
        # Response adaptation rules
        self.adaptation_rules = {
            "high_urgency": {
                "speaking_rate": 1.2,
                "emphasis_strength": 0.8,
                "directness": 0.9
            },
            "low_satisfaction": {
                "empathy_level": 0.9,
                "speaking_rate": 0.9,
                "formality_level": 0.7
            },
            "high_engagement": {
                "enthusiasm_level": 0.8,
                "pitch_variation": 0.7,
                "confidence_level": 0.9
            },
            "confused_customer": {
                "speaking_rate": 0.8,
                "emphasis_strength": 0.6,
                "clarity_focus": 0.9
            }
        }
    
    async def generate_dynamic_response(self, 
                                      customer_context: CustomerContext,
                                      current_message: str,
                                      sentiment_analysis: SentimentAnalysis,
                                      scenario: Scenario) -> GeneratedResponse:
        """
        Generate a dynamic response adapted to customer context and sentiment
        """
        start_time = datetime.now()
        
        # Analyze context for response adaptation
        adaptations = await self._analyze_required_adaptations(
            customer_context, sentiment_analysis, scenario
        )
        
        # Select appropriate voice profile
        voice_profile = self._select_voice_profile(
            scenario, sentiment_analysis, customer_context
        )
        
        # Generate contextual response text
        response_text = await self._generate_contextual_text(
            customer_context, current_message, sentiment_analysis, scenario, adaptations
        )
        
        # Adapt voice characteristics
        adapted_voice_characteristics = self._adapt_voice_characteristics(
            voice_profile, sentiment_analysis, adaptations
        )
        
        # Generate audio with adapted characteristics
        audio_url, audio_duration = await self._generate_adaptive_audio(
            response_text, voice_profile, adapted_voice_characteristics
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_response_confidence(
            sentiment_analysis, adaptations, len(response_text)
        )
        
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return GeneratedResponse(
            text_response=response_text,
            voice_characteristics=adapted_voice_characteristics,
            audio_url=audio_url,
            audio_duration_ms=audio_duration,
            generation_time_ms=generation_time,
            confidence_score=confidence_score,
            response_style=self._determine_response_style(sentiment_analysis, scenario),
            adaptations_made=adaptations,
            generated_at=datetime.now()
        )
    
    async def _analyze_required_adaptations(self, 
                                          customer_context: CustomerContext,
                                          sentiment_analysis: SentimentAnalysis,
                                          scenario: Scenario) -> List[str]:
        """Analyze what adaptations are needed for the response"""
        adaptations = []
        
        # Urgency-based adaptations
        if sentiment_analysis.urgency_level > 0.7:
            adaptations.append("high_urgency")
        
        # Satisfaction-based adaptations
        if sentiment_analysis.satisfaction_score < 0.4:
            adaptations.append("low_satisfaction")
        
        # Engagement-based adaptations
        if sentiment_analysis.engagement_level > 0.7:
            adaptations.append("high_engagement")
        
        # Emotional state adaptations
        if sentiment_analysis.emotional_state == EmotionalState.CONFUSED:
            adaptations.append("confused_customer")
        elif sentiment_analysis.emotional_state == EmotionalState.FRUSTRATED:
            adaptations.append("frustrated_customer")
        elif sentiment_analysis.emotional_state == EmotionalState.ENTHUSIASTIC:
            adaptations.append("enthusiastic_customer")
        
        # Escalation risk adaptations
        if sentiment_analysis.escalation_risk > 0.6:
            adaptations.append("escalation_risk")
        
        # Scenario-specific adaptations
        if scenario == Scenario.SALES and customer_context.lead_score > 70:
            adaptations.append("qualified_lead")
        elif scenario == Scenario.SUPPORT and customer_context.priority == Priority.CRITICAL:
            adaptations.append("critical_support")
        
        return adaptations
    
    def _select_voice_profile(self, scenario: Scenario, 
                            sentiment_analysis: SentimentAnalysis,
                            customer_context: CustomerContext) -> VoiceProfile:
        """Select appropriate voice profile based on context"""
        
        # Scenario-based selection
        if scenario == Scenario.SALES:
            return VoiceProfile.SALES_SPECIALIST
        elif scenario == Scenario.SUPPORT:
            return VoiceProfile.SUPPORT_AGENT
        elif scenario in [Scenario.ESCALATION]:
            return VoiceProfile.EXECUTIVE
        elif sentiment_analysis.emotional_state == EmotionalState.CONFUSED:
            return VoiceProfile.TECHNICAL_EXPERT
        else:
            # Default to professional based on customer preference or context
            return VoiceProfile.PROFESSIONAL_FEMALE
    
    async def _generate_contextual_text(self, 
                                      customer_context: CustomerContext,
                                      current_message: str,
                                      sentiment_analysis: SentimentAnalysis,
                                      scenario: Scenario,
                                      adaptations: List[str]) -> str:
        """Generate contextually appropriate response text"""
        
        # Get comprehensive context
        full_context = await self.context_manager.build_comprehensive_context(
            customer_context.room_id, customer_context.participant_id
        )
        
        # Build dynamic prompt
        prompt = self._build_dynamic_prompt(
            customer_context, sentiment_analysis, scenario, adaptations, full_context
        )
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": current_message}
                ],
                temperature=0.3,
                max_tokens=150,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            generated_text = response.choices[0].message.content.strip()
            
            # Post-process for adaptations
            adapted_text = self._apply_text_adaptations(generated_text, adaptations)
            
            return adapted_text
            
        except Exception as e:
            logger.error(f"Failed to generate contextual text: {e}")
            return self._get_fallback_response(scenario, sentiment_analysis)
    
    def _build_dynamic_prompt(self, customer_context: CustomerContext,
                            sentiment_analysis: SentimentAnalysis,
                            scenario: Scenario, adaptations: List[str],
                            full_context: Dict[str, Any]) -> str:
        """Build dynamic prompt for text generation"""
        
        prompt_sections = [
            f"You are VoiceFlow Pro, responding in the {scenario.value} scenario.",
            f"Customer emotional state: {sentiment_analysis.emotional_state.value}",
            f"Sentiment polarity: {sentiment_analysis.polarity:.2f}",
            f"Satisfaction level: {sentiment_analysis.satisfaction_score:.2f}",
            f"Urgency level: {sentiment_analysis.urgency_level:.2f}",
            ""
        ]
        
        # Add customer context
        if customer_context.name:
            prompt_sections.append(f"Customer name: {customer_context.name}")
        if customer_context.company:
            prompt_sections.append(f"Company: {customer_context.company}")
        
        # Add adaptation instructions
        if "high_urgency" in adaptations:
            prompt_sections.append("URGENT: Respond quickly and directly.")
        if "low_satisfaction" in adaptations:
            prompt_sections.append("EMPATHY: Show understanding and apologize appropriately.")
        if "confused_customer" in adaptations:
            prompt_sections.append("CLARITY: Use simple language and explain clearly.")
        if "escalation_risk" in adaptations:
            prompt_sections.append("DE-ESCALATION: Be calm, solution-focused, and offer escalation.")
        
        # Add context-specific instructions
        prompt_sections.extend([
            "",
            "Response requirements:",
            "- Keep responses to 1-3 sentences maximum",
            "- Be natural and conversational",
            "- Reference customer by name when appropriate",
            "- Show continuity with previous interactions",
            "- End with a clear question or next step",
            ""
        ])
        
        return "\n".join(prompt_sections)
    
    def _apply_text_adaptations(self, text: str, adaptations: List[str]) -> str:
        """Apply text-level adaptations to generated response"""
        adapted_text = text
        
        # High urgency - make more direct
        if "high_urgency" in adaptations:
            adapted_text = adapted_text.replace("I'd be happy to", "I'll")
            adapted_text = adapted_text.replace("Let me see if I can", "I'll")
        
        # Low satisfaction - add empathy
        if "low_satisfaction" in adaptations:
            if not any(word in adapted_text.lower() for word in ["sorry", "apologize", "understand"]):
                adapted_text = "I understand your concern. " + adapted_text
        
        # Confused customer - simplify language
        if "confused_customer" in adaptations:
            # Simplify complex words (basic implementation)
            replacements = {
                "utilize": "use",
                "facilitate": "help",
                "implement": "set up",
                "configuration": "setup"
            }
            for complex_word, simple_word in replacements.items():
                adapted_text = adapted_text.replace(complex_word, simple_word)
        
        return adapted_text
    
    def _adapt_voice_characteristics(self, voice_profile: VoiceProfile,
                                   sentiment_analysis: SentimentAnalysis,
                                   adaptations: List[str]) -> VoiceCharacteristics:
        """Adapt voice characteristics based on context"""
        
        # Start with base characteristics
        base_chars = self.voice_profiles[voice_profile]["characteristics"]
        
        # Create adapted copy
        adapted_chars = VoiceCharacteristics(
            stability=base_chars.stability,
            similarity_boost=base_chars.similarity_boost,
            style=base_chars.style,
            use_speaker_boost=base_chars.use_speaker_boost,
            speaking_rate=base_chars.speaking_rate,
            pitch_variation=base_chars.pitch_variation,
            emphasis_strength=base_chars.emphasis_strength,
            formality_level=base_chars.formality_level,
            enthusiasm_level=base_chars.enthusiasm_level,
            empathy_level=base_chars.empathy_level,
            confidence_level=base_chars.confidence_level
        )
        
        # Apply adaptation rules
        for adaptation in adaptations:
            if adaptation in self.adaptation_rules:
                rules = self.adaptation_rules[adaptation]
                
                if "speaking_rate" in rules:
                    adapted_chars.speaking_rate = rules["speaking_rate"]
                if "emphasis_strength" in rules:
                    adapted_chars.emphasis_strength = rules["emphasis_strength"]
                if "empathy_level" in rules:
                    adapted_chars.empathy_level = rules["empathy_level"]
                if "enthusiasm_level" in rules:
                    adapted_chars.enthusiasm_level = rules["enthusiasm_level"]
        
        # Sentiment-based micro-adjustments
        if sentiment_analysis.emotional_state == EmotionalState.FRUSTRATED:
            adapted_chars.speaking_rate *= 0.9  # Slower, more careful
            adapted_chars.empathy_level = min(1.0, adapted_chars.empathy_level + 0.2)
        
        elif sentiment_analysis.emotional_state == EmotionalState.ENTHUSIASTIC:
            adapted_chars.enthusiasm_level = min(1.0, adapted_chars.enthusiasm_level + 0.3)
            adapted_chars.pitch_variation = min(1.0, adapted_chars.pitch_variation + 0.2)
        
        return adapted_chars
    
    async def _generate_adaptive_audio(self, text: str, voice_profile: VoiceProfile,
                                     voice_characteristics: VoiceCharacteristics) -> Tuple[Optional[str], int]:
        """Generate audio with adaptive voice characteristics"""
        try:
            # Get voice configuration
            voice_config = self.voice_profiles[voice_profile]
            voice_id = voice_config["voice_id"]
            
            # Create voice settings from characteristics
            voice_settings = VoiceSettings(
                stability=voice_characteristics.stability,
                similarity_boost=voice_characteristics.similarity_boost,
                style=voice_characteristics.style,
                use_speaker_boost=voice_characteristics.use_speaker_boost
            )
            
            # Generate audio
            audio = generate(
                text=text,
                voice=Voice(voice_id=voice_id, settings=voice_settings),
                model="eleven_turbo_v2",  # Fast, low-latency model
                stream=False
            )
            
            # Save to temporary file and upload (in production, use cloud storage)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                save(audio, temp_file.name)
                
                # In production, upload to CDN and return URL
                # For now, return local file path
                audio_url = f"/tmp/audio/{os.path.basename(temp_file.name)}"
                
                # Estimate duration (rough calculation)
                # In production, use actual audio analysis
                words = len(text.split())
                estimated_duration = int(words * (60000 / 150) / voice_characteristics.speaking_rate)
                
                return audio_url, estimated_duration
                
        except Exception as e:
            logger.error(f"Failed to generate adaptive audio: {e}")
            return None, 0
    
    def _calculate_response_confidence(self, sentiment_analysis: SentimentAnalysis,
                                     adaptations: List[str], text_length: int) -> float:
        """Calculate confidence score for generated response"""
        confidence_factors = []
        
        # Base confidence from sentiment analysis confidence
        confidence_factors.append(sentiment_analysis.confidence * 0.4)
        
        # Adaptation appropriateness
        adaptation_score = min(len(adaptations) / 5, 1.0) * 0.3  # More adaptations = higher confidence
        confidence_factors.append(adaptation_score)
        
        # Text length appropriateness (not too short, not too long)
        ideal_length = 100  # characters
        length_score = 1.0 - abs(text_length - ideal_length) / ideal_length
        length_score = max(0.0, min(1.0, length_score)) * 0.2
        confidence_factors.append(length_score)
        
        # Scenario match confidence
        scenario_confidence = 0.1  # Base scenario confidence
        confidence_factors.append(scenario_confidence)
        
        return sum(confidence_factors)
    
    def _determine_response_style(self, sentiment_analysis: SentimentAnalysis,
                                scenario: Scenario) -> ResponseStyle:
        """Determine appropriate response style"""
        
        if sentiment_analysis.emotional_state == EmotionalState.FRUSTRATED:
            return ResponseStyle.EMPATHETIC
        elif sentiment_analysis.emotional_state == EmotionalState.CONFUSED:
            return ResponseStyle.TECHNICAL
        elif scenario == Scenario.SALES:
            return ResponseStyle.PERSUASIVE
        elif scenario == Scenario.ESCALATION:
            return ResponseStyle.APOLOGETIC
        elif sentiment_analysis.engagement_level > 0.7:
            return ResponseStyle.ENTHUSIASTIC
        else:
            return ResponseStyle.CONVERSATIONAL
    
    def _get_fallback_response(self, scenario: Scenario, 
                             sentiment_analysis: SentimentAnalysis) -> str:
        """Get fallback response when generation fails"""
        fallback_responses = {
            Scenario.ONBOARDING: "Hello! I'm here to help with your business needs. How can I assist you today?",
            Scenario.SALES: "I'd be happy to discuss how we can help your business. What specific challenges are you facing?",
            Scenario.SUPPORT: "I understand you need assistance. Let me help you resolve this issue right away.",
            Scenario.SCHEDULING: "I can help you schedule an appointment. What type of meeting would work best for you?",
            Scenario.ESCALATION: "I apologize for any inconvenience. Let me connect you with someone who can help immediately."
        }
        
        return fallback_responses.get(scenario, "How can I help you today?")
    
    async def clone_voice_from_sample(self, audio_file_path: str, 
                                    voice_name: str, description: str) -> Optional[str]:
        """Clone a voice from audio sample for personalized responses"""
        try:
            # Clone voice using ElevenLabs
            voice = clone(
                name=voice_name,
                description=description,
                files=[audio_file_path]
            )
            
            logger.info(f"Successfully cloned voice: {voice_name}")
            return voice.voice_id
            
        except Exception as e:
            logger.error(f"Failed to clone voice: {e}")
            return None
    
    async def generate_personalized_greeting(self, customer_context: CustomerContext) -> GeneratedResponse:
        """Generate personalized greeting based on customer history"""
        
        # Get customer's previous interactions
        full_context = await self.context_manager.build_comprehensive_context(
            customer_context.room_id, customer_context.participant_id
        )
        
        # Create personalized greeting text
        greeting_text = await self._create_personalized_greeting_text(customer_context, full_context)
        
        # Use friendly voice profile for greetings
        voice_profile = VoiceProfile.FRIENDLY_FEMALE
        base_characteristics = self.voice_profiles[voice_profile]["characteristics"]
        
        # Generate greeting audio
        audio_url, duration = await self._generate_adaptive_audio(
            greeting_text, voice_profile, base_characteristics
        )
        
        return GeneratedResponse(
            text_response=greeting_text,
            voice_characteristics=base_characteristics,
            audio_url=audio_url,
            audio_duration_ms=duration,
            generation_time_ms=0,  # Greeting generation is typically fast
            confidence_score=0.9,  # High confidence for greetings
            response_style=ResponseStyle.CONVERSATIONAL,
            adaptations_made=["personalized_greeting"],
            generated_at=datetime.now()
        )
    
    async def _create_personalized_greeting_text(self, customer_context: CustomerContext,
                                               full_context: Dict[str, Any]) -> str:
        """Create personalized greeting text"""
        
        base_greeting = "Hello"
        
        # Add name if available
        if customer_context.name:
            base_greeting += f", {customer_context.name}"
        
        # Add context-based personalization
        contexts = full_context.get('context_layers', {})
        
        if 'long_term' in contexts:
            long_term = contexts['long_term']
            relationship_stage = long_term.get('relationship_stage', 'new')
            
            if relationship_stage == 'customer':
                base_greeting += "! Welcome back to VoiceFlow Pro."
            elif relationship_stage == 'prospect':
                base_greeting += "! Thanks for your continued interest in VoiceFlow Pro."
            else:
                base_greeting += "! Welcome to VoiceFlow Pro."
        else:
            base_greeting += "! Welcome to VoiceFlow Pro."
        
        # Add appropriate follow-up
        base_greeting += " I'm here to help with your business needs. How can I assist you today?"
        
        return base_greeting