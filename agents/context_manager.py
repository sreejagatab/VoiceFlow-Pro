"""
Advanced Context-Aware Conversation Management for VoiceFlow Pro

This module implements sophisticated conversation context management that:
- Maintains context across multiple agent sessions
- Provides intelligent conversation continuity
- Manages long-term customer relationship memory
- Handles context-aware response generation
"""

import asyncio
import logging
import json
import pickle
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import aioredis
import openai

from voice_agent import CustomerContext, Scenario, Priority

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of conversation context"""
    SHORT_TERM = "short_term"      # Current session (last 10-15 exchanges)
    MEDIUM_TERM = "medium_term"    # Recent sessions (last 24-48 hours)
    LONG_TERM = "long_term"        # Historical relationship (weeks/months)
    GLOBAL = "global"              # Company-wide context and policies


class ConversationIntent(Enum):
    """Refined conversation intents for better context management"""
    GREETING = "greeting"
    INFORMATION_SEEKING = "information_seeking"
    PROBLEM_SOLVING = "problem_solving"
    DECISION_MAKING = "decision_making"
    RELATIONSHIP_BUILDING = "relationship_building"
    TRANSACTION = "transaction"
    FOLLOW_UP = "follow_up"
    ESCALATION = "escalation"


@dataclass
class ContextualMemory:
    """Structured memory for conversation context"""
    # Core identification
    customer_id: str
    session_id: str
    created_at: datetime
    last_accessed: datetime
    
    # Conversation context
    conversation_summary: str
    key_topics: List[str]
    unresolved_issues: List[Dict[str, Any]]
    commitments_made: List[Dict[str, Any]]
    customer_preferences: Dict[str, Any]
    
    # Business context
    relationship_stage: str  # prospect, customer, advocate, at_risk
    interaction_history: List[Dict[str, Any]]
    business_value: float
    satisfaction_trend: List[float]
    
    # Technical context
    system_performance: Dict[str, Any]
    integration_status: Dict[str, Any]
    feature_usage: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_accessed'] = self.last_accessed.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextualMemory':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)


class AdvancedContextManager:
    """
    Advanced conversation context management with multi-layered memory
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.openai_client = openai.AsyncOpenAI()
        
        # Context storage keys
        self.context_keys = {
            ContextType.SHORT_TERM: "ctx:short:{customer_id}:{session_id}",
            ContextType.MEDIUM_TERM: "ctx:medium:{customer_id}",
            ContextType.LONG_TERM: "ctx:long:{customer_id}",
            ContextType.GLOBAL: "ctx:global:policies"
        }
        
        # Context retention periods
        self.retention_periods = {
            ContextType.SHORT_TERM: timedelta(hours=6),
            ContextType.MEDIUM_TERM: timedelta(days=7),
            ContextType.LONG_TERM: timedelta(days=90),
            ContextType.GLOBAL: None  # Permanent
        }
        
        # Context weights for response generation
        self.context_weights = {
            ContextType.SHORT_TERM: 0.4,
            ContextType.MEDIUM_TERM: 0.3,
            ContextType.LONG_TERM: 0.2,
            ContextType.GLOBAL: 0.1
        }
    
    async def initialize(self):
        """Initialize Redis connection and context manager"""
        try:
            self.redis_client = await aioredis.from_url(self.redis_url)
            logger.info("Context manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize context manager: {e}")
            raise
    
    async def store_context(self, customer_id: str, session_id: str, 
                          context_type: ContextType, context_data: Dict[str, Any]):
        """Store conversation context with appropriate retention"""
        if not self.redis_client:
            await self.initialize()
        
        key = self.context_keys[context_type].format(
            customer_id=customer_id, 
            session_id=session_id
        )
        
        # Add metadata
        context_data.update({
            'stored_at': datetime.now().isoformat(),
            'context_type': context_type.value,
            'customer_id': customer_id,
            'session_id': session_id
        })
        
        try:
            # Store with appropriate TTL
            retention = self.retention_periods[context_type]
            if retention:
                await self.redis_client.setex(
                    key, 
                    int(retention.total_seconds()), 
                    json.dumps(context_data)
                )
            else:
                await self.redis_client.set(key, json.dumps(context_data))
            
            logger.info(f"Stored {context_type.value} context for customer {customer_id}")
            
        except Exception as e:
            logger.error(f"Failed to store context: {e}")
    
    async def retrieve_context(self, customer_id: str, session_id: str, 
                             context_type: ContextType) -> Optional[Dict[str, Any]]:
        """Retrieve specific context type"""
        if not self.redis_client:
            await self.initialize()
        
        key = self.context_keys[context_type].format(
            customer_id=customer_id, 
            session_id=session_id
        )
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return None
    
    async def build_comprehensive_context(self, customer_id: str, 
                                        session_id: str) -> Dict[str, Any]:
        """Build comprehensive context from all layers"""
        contexts = {}
        
        # Retrieve all context types
        for context_type in ContextType:
            context = await self.retrieve_context(customer_id, session_id, context_type)
            if context:
                contexts[context_type.value] = context
        
        # Build weighted context summary
        comprehensive_context = {
            'customer_id': customer_id,
            'session_id': session_id,
            'retrieved_at': datetime.now().isoformat(),
            'available_contexts': list(contexts.keys()),
            'context_layers': contexts
        }
        
        return comprehensive_context
    
    async def generate_context_aware_response(self, customer_context: CustomerContext, 
                                            current_message: str, 
                                            scenario: Scenario) -> str:
        """Generate response using full contextual awareness"""
        
        # Get comprehensive context
        full_context = await self.build_comprehensive_context(
            customer_context.room_id, 
            customer_context.participant_id
        )
        
        # Build context-aware prompt
        context_prompt = self._build_contextual_prompt(
            customer_context, current_message, scenario, full_context
        )
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": context_prompt},
                    {"role": "user", "content": current_message}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            generated_response = response.choices[0].message.content
            
            # Update short-term context with this exchange
            await self._update_short_term_context(
                customer_context, current_message, generated_response, scenario
            )
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Failed to generate context-aware response: {e}")
            return "I apologize, but I'm having trouble accessing our conversation history. How can I help you today?"
    
    def _build_contextual_prompt(self, customer_context: CustomerContext, 
                                current_message: str, scenario: Scenario, 
                                full_context: Dict[str, Any]) -> str:
        """Build sophisticated contextual prompt for LLM"""
        
        prompt_sections = [
            "You are VoiceFlow Pro, an advanced business automation voice agent with deep contextual awareness.",
            ""
        ]
        
        # Add customer identification context
        if customer_context.name:
            prompt_sections.append(f"Customer: {customer_context.name}")
        if customer_context.company:
            prompt_sections.append(f"Company: {customer_context.company}")
        
        # Add historical context if available
        contexts = full_context.get('context_layers', {})
        
        if 'long_term' in contexts:
            long_term = contexts['long_term']
            prompt_sections.extend([
                "",
                "LONG-TERM RELATIONSHIP CONTEXT:",
                f"- Relationship stage: {long_term.get('relationship_stage', 'unknown')}",
                f"- Business value: {long_term.get('business_value', 'unknown')}",
                f"- Key preferences: {', '.join(long_term.get('customer_preferences', {}).keys())}"
            ])
        
        if 'medium_term' in contexts:
            medium_term = contexts['medium_term']
            prompt_sections.extend([
                "",
                "RECENT INTERACTION CONTEXT:",
                f"- Recent topics: {', '.join(medium_term.get('key_topics', [])[:3])}",
                f"- Unresolved issues: {len(medium_term.get('unresolved_issues', []))}",
                f"- Commitments made: {len(medium_term.get('commitments_made', []))}"
            ])
        
        if 'short_term' in contexts:
            short_term = contexts['short_term']
            if short_term.get('conversation_summary'):
                prompt_sections.extend([
                    "",
                    "CURRENT SESSION CONTEXT:",
                    f"- Session summary: {short_term['conversation_summary']}"
                ])
        
        # Add current scenario context
        prompt_sections.extend([
            "",
            f"CURRENT SCENARIO: {scenario.value.upper()}",
            f"Current lead score: {customer_context.lead_score}",
            f"Priority level: {customer_context.priority.value}",
            ""
        ])
        
        # Add scenario-specific instructions
        scenario_instructions = {
            Scenario.ONBOARDING: "Focus on understanding needs and building rapport. Reference any previous interactions warmly.",
            Scenario.SALES: "Leverage relationship context to personalize value propositions. Reference previous discussions about requirements.",
            Scenario.SUPPORT: "Check for related previous issues. Show continuity in problem-solving approach.",
            Scenario.SCHEDULING: "Consider previous meeting preferences and availability patterns.",
            Scenario.FOLLOW_UP: "Reference specific previous commitments and check on outcomes.",
            Scenario.ESCALATION: "Summarize full context for smooth handoff to human agent."
        }
        
        prompt_sections.append(f"SCENARIO GUIDANCE: {scenario_instructions.get(scenario, 'Handle professionally with context awareness.')}")
        
        # Add response guidelines
        prompt_sections.extend([
            "",
            "RESPONSE GUIDELINES:",
            "- Reference relevant context naturally without being overwhelming",
            "- Show continuity with previous interactions when appropriate",
            "- Adapt tone based on relationship stage and history",
            "- Keep responses concise but contextually rich",
            "- Acknowledge any changes since last interaction",
            ""
        ])
        
        return "\n".join(prompt_sections)
    
    async def _update_short_term_context(self, customer_context: CustomerContext, 
                                       user_message: str, agent_response: str, 
                                       scenario: Scenario):
        """Update short-term context with new conversation turn"""
        
        # Get existing short-term context
        existing_context = await self.retrieve_context(
            customer_context.room_id, 
            customer_context.participant_id, 
            ContextType.SHORT_TERM
        ) or {}
        
        # Extract key information from the exchange
        exchange_summary = await self._summarize_exchange(
            user_message, agent_response, scenario
        )
        
        # Update context
        conversation_turns = existing_context.get('conversation_turns', [])
        conversation_turns.append({
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'agent_response': agent_response,
            'scenario': scenario.value,
            'summary': exchange_summary
        })
        
        # Keep only last 10 turns for short-term context
        conversation_turns = conversation_turns[-10:]
        
        # Generate overall session summary
        session_summary = await self._generate_session_summary(conversation_turns)
        
        short_term_context = {
            'conversation_turns': conversation_turns,
            'session_summary': session_summary,
            'last_scenario': scenario.value,
            'key_topics': await self._extract_key_topics(conversation_turns),
            'customer_sentiment': customer_context.sentiment_scores[-5:] if customer_context.sentiment_scores else [],
            'lead_score_progression': [customer_context.lead_score]
        }
        
        # Store updated context
        await self.store_context(
            customer_context.room_id,
            customer_context.participant_id,
            ContextType.SHORT_TERM,
            short_term_context
        )
    
    async def _summarize_exchange(self, user_message: str, agent_response: str, 
                                scenario: Scenario) -> str:
        """Generate concise summary of conversation exchange"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"Summarize this conversation exchange in one concise sentence:\n\nCustomer: {user_message}\nAgent: {agent_response}\nScenario: {scenario.value}"
                }],
                temperature=0.2,
                max_tokens=50
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to summarize exchange: {e}")
            return f"Customer discussed {scenario.value} topics"
    
    async def _generate_session_summary(self, conversation_turns: List[Dict]) -> str:
        """Generate summary of entire session"""
        if not conversation_turns:
            return "New session started"
        
        try:
            # Create a condensed version of the conversation
            conversation_text = "\n".join([
                f"Turn {i+1}: {turn.get('summary', 'No summary')}"
                for i, turn in enumerate(conversation_turns)
            ])
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"Create a concise summary of this conversation session:\n\n{conversation_text}"
                }],
                temperature=0.2,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return "Session with multiple conversation turns"
    
    async def _extract_key_topics(self, conversation_turns: List[Dict]) -> List[str]:
        """Extract key topics from conversation"""
        if not conversation_turns:
            return []
        
        try:
            summaries = [turn.get('summary', '') for turn in conversation_turns]
            combined_text = " ".join(summaries)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": f"Extract 3-5 key topics from this conversation as a comma-separated list:\n\n{combined_text}"
                }],
                temperature=0.2,
                max_tokens=50
            )
            
            topics = response.choices[0].message.content.strip()
            return [topic.strip() for topic in topics.split(',')][:5]
            
        except Exception as e:
            logger.error(f"Failed to extract key topics: {e}")
            return ["general inquiry"]
    
    async def prepare_session_handoff(self, customer_id: str, session_id: str, 
                                    handoff_type: str) -> Dict[str, Any]:
        """Prepare comprehensive context for session handoff"""
        
        # Get full context
        full_context = await self.build_comprehensive_context(customer_id, session_id)
        
        # Create handoff package
        handoff_package = {
            'customer_id': customer_id,
            'session_id': session_id,
            'handoff_type': handoff_type,
            'handoff_time': datetime.now().isoformat(),
            'context_summary': await self._create_handoff_summary(full_context),
            'full_context': full_context,
            'recommended_actions': await self._suggest_handoff_actions(full_context, handoff_type)
        }
        
        # Store handoff package for human agent access
        await self.store_context(
            customer_id, 
            f"handoff-{session_id}", 
            ContextType.SHORT_TERM, 
            handoff_package
        )
        
        return handoff_package
    
    async def _create_handoff_summary(self, full_context: Dict[str, Any]) -> str:
        """Create executive summary for handoff"""
        try:
            context_text = json.dumps(full_context, indent=2)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "user",
                    "content": f"Create a professional handoff summary for a human agent based on this context:\n\n{context_text}\n\nInclude: customer background, current issue/need, conversation highlights, and recommended next steps."
                }],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to create handoff summary: {e}")
            return "Customer requires human assistance. Please review full conversation context."
    
    async def _suggest_handoff_actions(self, full_context: Dict[str, Any], 
                                     handoff_type: str) -> List[str]:
        """Suggest actions for human agent"""
        base_actions = [
            "Review customer conversation history",
            "Confirm understanding of current issue/need",
            "Reference previous commitments if any"
        ]
        
        handoff_specific_actions = {
            'escalation': [
                "Address escalation concern immediately",
                "Apologize for any previous issues",
                "Provide direct contact information for follow-up"
            ],
            'technical': [
                "Review technical context and error details",
                "Prepare screen sharing if needed",
                "Have development team on standby if complex"
            ],
            'sales': [
                "Review lead score and qualification status",
                "Prepare custom demo if appropriate",
                "Have pricing information ready"
            ]
        }
        
        return base_actions + handoff_specific_actions.get(handoff_type, [])
    
    async def cleanup_expired_contexts(self):
        """Clean up expired contexts (scheduled task)"""
        if not self.redis_client:
            return
        
        try:
            # Redis TTL handles most cleanup automatically
            # This method can be used for additional cleanup logic
            logger.info("Context cleanup completed")
        except Exception as e:
            logger.error(f"Context cleanup failed: {e}")
    
    async def close(self):
        """Clean up resources"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Context manager closed")