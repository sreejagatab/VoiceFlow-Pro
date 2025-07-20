"""
Advanced Sentiment Analysis with LiveKit Integration for VoiceFlow Pro

This module provides sophisticated sentiment analysis that:
- Integrates with LiveKit events for real-time processing
- Analyzes emotional undertones beyond basic positive/negative
- Provides actionable insights for conversation management
- Triggers appropriate response adjustments
"""

import asyncio
import logging
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import re
from textblob import TextBlob
import openai
from livekit import rtc

logger = logging.getLogger(__name__)


class EmotionalState(Enum):
    """Detailed emotional states beyond simple sentiment"""
    ENTHUSIASTIC = "enthusiastic"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    CONCERNED = "concerned"
    IMPATIENT = "impatient"
    INTERESTED = "interested"
    SKEPTICAL = "skeptical"


class SentimentTrend(Enum):
    """Sentiment trend over conversation"""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class SentimentAnalysis:
    """Comprehensive sentiment analysis result"""
    # Basic sentiment
    polarity: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    
    # Emotional analysis
    emotional_state: EmotionalState
    intensity: float  # 0.0 to 1.0
    
    # Contextual factors
    urgency_level: float  # 0.0 to 1.0
    satisfaction_score: float  # 0.0 to 1.0
    engagement_level: float  # 0.0 to 1.0
    
    # Conversation dynamics
    question_ratio: float  # Ratio of questions in text
    complexity_score: float  # Language complexity
    assertiveness: float  # How assertive the speaker is
    
    # Actionable insights
    recommended_response_tone: str
    suggested_actions: List[str]
    escalation_risk: float  # 0.0 to 1.0
    
    # Metadata
    analyzed_at: datetime
    text_length: int
    processing_time_ms: float


class AdvancedSentimentAnalyzer:
    """
    Advanced sentiment analysis with LiveKit integration
    """
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI()
        
        # Sentiment analysis patterns
        self.emotion_patterns = {
            EmotionalState.ENTHUSIASTIC: [
                r'\b(amazing|fantastic|perfect|excellent|love|great)\b',
                r'\b(excited|thrilled|wonderful|awesome)\b',
                r'!{2,}',  # Multiple exclamation marks
            ],
            EmotionalState.FRUSTRATED: [
                r'\b(frustrated|annoying|ridiculous|terrible|awful)\b',
                r'\b(why (can\'t|won\'t|don\'t))\b',
                r'\b(this is (so|really) (hard|difficult|confusing))\b',
            ],
            EmotionalState.CONFUSED: [
                r'\b(confused|unclear|don\'t understand|what (do you )?mean)\b',
                r'\b(how (do|does)|what (is|are))\b.*\?',
                r'\b(I\'m (not )?sure)\b',
            ],
            EmotionalState.IMPATIENT: [
                r'\b(when|how long|hurry|quickly|asap|urgent)\b',
                r'\b(waiting (for )?too long|taking forever)\b',
                r'\b(can we (just|please))\b',
            ],
            EmotionalState.SKEPTICAL: [
                r'\b(really\?|are you sure|I doubt|questionable)\b',
                r'\b(sounds (too )?good|seems (too )?easy)\b',
                r'\b(I\'ve heard (that )?before)\b',
            ]
        }
        
        # Urgency indicators
        self.urgency_patterns = [
            r'\b(urgent|emergency|asap|immediately|right now)\b',
            r'\b(critical|important|serious|major)\b',
            r'\b(need (it|this) (today|now|quickly))\b',
            r'\b(can\'t wait|running out of time)\b'
        ]
        
        # Satisfaction indicators
        self.satisfaction_patterns = {
            'positive': [
                r'\b(thank you|thanks|appreciate|helpful|satisfied)\b',
                r'\b(exactly|perfect|that works|sounds good)\b',
                r'\b(you\'ve been (great|helpful|amazing))\b'
            ],
            'negative': [
                r'\b(disappointed|unhappy|not satisfied|problem)\b',
                r'\b(doesn\'t work|not working|broken|issues)\b',
                r'\b(waste of time|money|effort)\b'
            ]
        }
        
        # Engagement indicators
        self.engagement_patterns = [
            r'\?',  # Questions indicate engagement
            r'\b(tell me more|what about|how about|what if)\b',
            r'\b(I want to|I\'d like to|can you)\b',
            r'\b(let\'s|we should|we could)\b'
        ]
        
        # Conversation history for trend analysis
        self.sentiment_history: Dict[str, List[SentimentAnalysis]] = {}
        
    async def analyze_comprehensive_sentiment(self, text: str, 
                                            speaker_id: str = None,
                                            context: Dict[str, Any] = None) -> SentimentAnalysis:
        """
        Perform comprehensive sentiment analysis
        """
        start_time = datetime.now()
        
        # Basic sentiment analysis
        blob = TextBlob(text)
        basic_polarity = blob.sentiment.polarity
        basic_subjectivity = blob.sentiment.subjectivity
        
        # Emotional state detection
        emotional_state = self._detect_emotional_state(text)
        intensity = self._calculate_intensity(text, emotional_state)
        
        # Contextual analysis
        urgency_level = self._calculate_urgency(text)
        satisfaction_score = self._calculate_satisfaction(text)
        engagement_level = self._calculate_engagement(text)
        
        # Conversation dynamics
        question_ratio = self._calculate_question_ratio(text)
        complexity_score = self._calculate_complexity(text)
        assertiveness = self._calculate_assertiveness(text)
        
        # Advanced analysis using OpenAI for nuanced understanding
        ai_analysis = await self._get_ai_sentiment_analysis(text, context)
        
        # Generate actionable insights
        recommended_tone = self._recommend_response_tone(
            basic_polarity, emotional_state, urgency_level, satisfaction_score
        )
        suggested_actions = self._suggest_actions(
            emotional_state, urgency_level, satisfaction_score, engagement_level
        )
        escalation_risk = self._calculate_escalation_risk(
            basic_polarity, emotional_state, urgency_level, satisfaction_score
        )
        
        # Create comprehensive analysis
        analysis = SentimentAnalysis(
            polarity=basic_polarity,
            confidence=1.0 - basic_subjectivity,  # Higher subjectivity = lower confidence
            emotional_state=emotional_state,
            intensity=intensity,
            urgency_level=urgency_level,
            satisfaction_score=satisfaction_score,
            engagement_level=engagement_level,
            question_ratio=question_ratio,
            complexity_score=complexity_score,
            assertiveness=assertiveness,
            recommended_response_tone=recommended_tone,
            suggested_actions=suggested_actions,
            escalation_risk=escalation_risk,
            analyzed_at=datetime.now(),
            text_length=len(text),
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
        )
        
        # Store in history for trend analysis
        if speaker_id:
            if speaker_id not in self.sentiment_history:
                self.sentiment_history[speaker_id] = []
            self.sentiment_history[speaker_id].append(analysis)
            
            # Keep only last 20 analyses
            self.sentiment_history[speaker_id] = self.sentiment_history[speaker_id][-20:]
        
        return analysis
    
    def _detect_emotional_state(self, text: str) -> EmotionalState:
        """Detect specific emotional state from text"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, patterns in self.emotion_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            emotion_scores[emotion] = score
        
        # Return emotion with highest score, default to neutral
        if max(emotion_scores.values()) > 0:
            return max(emotion_scores, key=emotion_scores.get)
        
        # Fallback to basic sentiment-based classification
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.5:
            return EmotionalState.SATISFIED
        elif polarity > 0.1:
            return EmotionalState.INTERESTED
        elif polarity < -0.5:
            return EmotionalState.FRUSTRATED
        elif polarity < -0.1:
            return EmotionalState.CONCERNED
        else:
            return EmotionalState.NEUTRAL
    
    def _calculate_intensity(self, text: str, emotional_state: EmotionalState) -> float:
        """Calculate emotional intensity"""
        intensity_indicators = [
            len(re.findall(r'!', text)) * 0.1,  # Exclamation marks
            len(re.findall(r'[A-Z]{2,}', text)) * 0.15,  # CAPS
            len(re.findall(r'\b(very|extremely|really|so|totally)\b', text.lower())) * 0.1,
            len(re.findall(r'\b(absolutely|completely|definitely|certainly)\b', text.lower())) * 0.1
        ]
        
        base_intensity = min(sum(intensity_indicators), 1.0)
        
        # Adjust based on emotional state
        if emotional_state in [EmotionalState.ANGRY, EmotionalState.FRUSTRATED]:
            base_intensity *= 1.2
        elif emotional_state in [EmotionalState.ENTHUSIASTIC]:
            base_intensity *= 1.1
        
        return min(base_intensity, 1.0)
    
    def _calculate_urgency(self, text: str) -> float:
        """Calculate urgency level"""
        urgency_score = 0
        text_lower = text.lower()
        
        for pattern in self.urgency_patterns:
            matches = len(re.findall(pattern, text_lower))
            urgency_score += matches * 0.2
        
        # Time-related urgency
        time_patterns = [
            r'\b(today|now|immediately|asap)\b',
            r'\b(this (morning|afternoon|evening))\b',
            r'\b(by (end of|close of) (day|business))\b'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, text_lower):
                urgency_score += 0.3
        
        return min(urgency_score, 1.0)
    
    def _calculate_satisfaction(self, text: str) -> float:
        """Calculate satisfaction score"""
        positive_score = 0
        negative_score = 0
        text_lower = text.lower()
        
        for pattern in self.satisfaction_patterns['positive']:
            positive_score += len(re.findall(pattern, text_lower)) * 0.2
        
        for pattern in self.satisfaction_patterns['negative']:
            negative_score += len(re.findall(pattern, text_lower)) * 0.2
        
        # Normalize to 0-1 scale with 0.5 as neutral
        net_satisfaction = positive_score - negative_score
        return max(0.0, min(1.0, 0.5 + net_satisfaction))
    
    def _calculate_engagement(self, text: str) -> float:
        """Calculate engagement level"""
        engagement_score = 0
        text_lower = text.lower()
        
        for pattern in self.engagement_patterns:
            matches = len(re.findall(pattern, text_lower))
            engagement_score += matches * 0.15
        
        # Length-based engagement (longer responses often indicate higher engagement)
        word_count = len(text.split())
        if word_count > 50:
            engagement_score += 0.2
        elif word_count > 20:
            engagement_score += 0.1
        
        return min(engagement_score, 1.0)
    
    def _calculate_question_ratio(self, text: str) -> float:
        """Calculate ratio of questions in text"""
        sentences = re.split(r'[.!?]+', text)
        questions = len(re.findall(r'\?', text))
        total_sentences = len([s for s in sentences if s.strip()])
        
        return questions / max(total_sentences, 1)
    
    def _calculate_complexity(self, text: str) -> float:
        """Calculate language complexity"""
        words = text.split()
        if not words:
            return 0.0
        
        # Average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Sentence length
        sentences = re.split(r'[.!?]+', text)
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        # Complex words (more than 6 characters)
        complex_words = sum(1 for word in words if len(word) > 6)
        complexity_ratio = complex_words / len(words)
        
        # Normalize complexity score
        complexity = (avg_word_length / 10 + avg_sentence_length / 20 + complexity_ratio) / 3
        return min(complexity, 1.0)
    
    def _calculate_assertiveness(self, text: str) -> float:
        """Calculate assertiveness level"""
        assertive_patterns = [
            r'\b(I want|I need|I require|I demand)\b',
            r'\b(you should|you must|you need to)\b',
            r'\b(make sure|ensure that|guarantee)\b',
            r'\b(I expect|I insist|I won\'t accept)\b'
        ]
        
        assertiveness_score = 0
        text_lower = text.lower()
        
        for pattern in assertive_patterns:
            matches = len(re.findall(pattern, text_lower))
            assertiveness_score += matches * 0.2
        
        # Imperative sentences
        imperatives = len(re.findall(r'\b(do|give|send|provide|fix|resolve)\b', text_lower))
        assertiveness_score += imperatives * 0.1
        
        return min(assertiveness_score, 1.0)
    
    async def _get_ai_sentiment_analysis(self, text: str, 
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get advanced sentiment analysis from OpenAI"""
        try:
            prompt = f"""
            Analyze the sentiment and emotional context of this customer message:
            
            Message: "{text}"
            
            Provide analysis in this format:
            - Primary emotion: [emotion]
            - Confidence level: [0-100]
            - Business impact: [positive/neutral/negative]
            - Response urgency: [low/medium/high]
            - Key concerns: [list any specific concerns]
            """
            
            if context:
                prompt += f"\nAdditional context: {json.dumps(context, indent=2)}"
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            
            # Parse the response (simplified for now)
            ai_response = response.choices[0].message.content
            return {"ai_analysis": ai_response}
            
        except Exception as e:
            logger.error(f"AI sentiment analysis failed: {e}")
            return {"ai_analysis": "Analysis unavailable"}
    
    def _recommend_response_tone(self, polarity: float, emotional_state: EmotionalState,
                                urgency: float, satisfaction: float) -> str:
        """Recommend appropriate response tone"""
        
        if emotional_state == EmotionalState.ANGRY or satisfaction < 0.3:
            return "empathetic_apologetic"
        elif emotional_state == EmotionalState.FRUSTRATED or urgency > 0.7:
            return "understanding_solution_focused"
        elif emotional_state == EmotionalState.CONFUSED:
            return "patient_explanatory"
        elif emotional_state == EmotionalState.ENTHUSIASTIC or satisfaction > 0.7:
            return "positive_engaging"
        elif emotional_state == EmotionalState.SKEPTICAL:
            return "reassuring_evidence_based"
        elif emotional_state == EmotionalState.IMPATIENT:
            return "efficient_direct"
        else:
            return "professional_helpful"
    
    def _suggest_actions(self, emotional_state: EmotionalState, urgency: float,
                        satisfaction: float, engagement: float) -> List[str]:
        """Suggest actions based on sentiment analysis"""
        actions = []
        
        if emotional_state == EmotionalState.ANGRY:
            actions.extend([
                "Acknowledge the customer's frustration",
                "Apologize for the negative experience",
                "Offer immediate escalation to supervisor"
            ])
        
        if urgency > 0.7:
            actions.extend([
                "Prioritize this conversation",
                "Provide immediate timeline",
                "Offer expedited solutions"
            ])
        
        if satisfaction < 0.4:
            actions.extend([
                "Investigate root cause of dissatisfaction",
                "Offer compensation or goodwill gesture",
                "Follow up to ensure resolution"
            ])
        
        if engagement > 0.7:
            actions.extend([
                "Capitalize on high engagement",
                "Provide additional value",
                "Consider upsell opportunities"
            ])
        
        if emotional_state == EmotionalState.CONFUSED:
            actions.extend([
                "Simplify explanations",
                "Use visual aids if possible",
                "Check understanding frequently"
            ])
        
        return actions
    
    def _calculate_escalation_risk(self, polarity: float, emotional_state: EmotionalState,
                                 urgency: float, satisfaction: float) -> float:
        """Calculate risk of conversation escalation"""
        risk_factors = []
        
        # Negative sentiment
        if polarity < -0.3:
            risk_factors.append(0.3)
        
        # Problematic emotional states
        if emotional_state in [EmotionalState.ANGRY, EmotionalState.FRUSTRATED]:
            risk_factors.append(0.4)
        
        # High urgency
        if urgency > 0.6:
            risk_factors.append(0.2)
        
        # Low satisfaction
        if satisfaction < 0.3:
            risk_factors.append(0.3)
        
        # Calculate compound risk
        if not risk_factors:
            return 0.0
        
        # Risk compounds but doesn't simply add
        total_risk = 1.0 - np.prod([1.0 - factor for factor in risk_factors])
        return min(total_risk, 1.0)
    
    def analyze_sentiment_trend(self, speaker_id: str, 
                              window_size: int = 10) -> Tuple[SentimentTrend, float]:
        """Analyze sentiment trend over conversation"""
        if speaker_id not in self.sentiment_history:
            return SentimentTrend.STABLE, 0.0
        
        history = self.sentiment_history[speaker_id]
        if len(history) < 3:
            return SentimentTrend.STABLE, 0.0
        
        # Get recent sentiment scores
        recent_scores = [analysis.polarity for analysis in history[-window_size:]]
        
        # Calculate trend
        if len(recent_scores) < 3:
            return SentimentTrend.STABLE, 0.0
        
        # Simple linear trend calculation
        x = np.arange(len(recent_scores))
        slope = np.polyfit(x, recent_scores, 1)[0]
        
        # Calculate volatility
        volatility = np.std(recent_scores)
        
        # Determine trend
        if volatility > 0.3:
            return SentimentTrend.VOLATILE, slope
        elif slope > 0.1:
            return SentimentTrend.IMPROVING, slope
        elif slope < -0.1:
            return SentimentTrend.DECLINING, slope
        else:
            return SentimentTrend.STABLE, slope
    
    async def process_livekit_audio_event(self, event: rtc.TrackEvent, 
                                        room_context: Dict[str, Any]) -> Optional[SentimentAnalysis]:
        """Process LiveKit audio events for real-time sentiment analysis"""
        try:
            # This would integrate with speech-to-text to get real-time transcription
            # For now, we'll simulate this with the assumption that we have transcript
            
            if hasattr(event, 'transcript') and event.transcript:
                return await self.analyze_comprehensive_sentiment(
                    event.transcript,
                    event.participant.identity,
                    room_context
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to process LiveKit audio event: {e}")
            return None
    
    def get_sentiment_summary(self, speaker_id: str) -> Dict[str, Any]:
        """Get comprehensive sentiment summary for a speaker"""
        if speaker_id not in self.sentiment_history:
            return {"error": "No sentiment history found"}
        
        history = self.sentiment_history[speaker_id]
        if not history:
            return {"error": "Empty sentiment history"}
        
        # Calculate averages
        avg_polarity = np.mean([a.polarity for a in history])
        avg_satisfaction = np.mean([a.satisfaction_score for a in history])
        avg_engagement = np.mean([a.engagement_level for a in history])
        avg_urgency = np.mean([a.urgency_level for a in history])
        
        # Get trend
        trend, trend_slope = self.analyze_sentiment_trend(speaker_id)
        
        # Most common emotional state
        emotional_states = [a.emotional_state for a in history]
        most_common_emotion = max(set(emotional_states), key=emotional_states.count)
        
        # Current escalation risk
        current_risk = history[-1].escalation_risk if history else 0.0
        
        return {
            "total_analyses": len(history),
            "average_sentiment": avg_polarity,
            "average_satisfaction": avg_satisfaction,
            "average_engagement": avg_engagement,
            "average_urgency": avg_urgency,
            "sentiment_trend": trend.value,
            "trend_slope": trend_slope,
            "most_common_emotion": most_common_emotion.value,
            "current_escalation_risk": current_risk,
            "last_analysis": history[-1].analyzed_at.isoformat()
        }