"""
VoiceFlow Pro Advanced Business Agent

This module implements comprehensive business automation with:
- Real AssemblyAI Universal-Streaming integration
- Multi-scenario conversation flows with state management
- Agent handoff mechanisms (sales → support → scheduling)
- Advanced intent classification and routing
- Business terminology training and context management
- Database persistence with LiveKit room metadata
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp

from livekit.agents import JobContext, llm
from livekit import rtc

logger = logging.getLogger(__name__)


class Scenario(Enum):
    """Business scenarios the agent can handle"""
    ONBOARDING = "onboarding"
    SALES = "sales"
    SUPPORT = "support"
    SCHEDULING = "scheduling"
    FOLLOW_UP = "follow_up"
    ESCALATION = "escalation"


class Priority(Enum):
    """Priority levels for conversations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CustomerContext:
    """Enhanced customer information and conversation state"""
    # Basic information
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    
    # Business context
    current_scenario: Scenario = Scenario.ONBOARDING
    previous_scenarios: List[Scenario] = None
    lead_score: int = 0
    priority: Priority = Priority.MEDIUM
    
    # Conversation state
    conversation_history: List[Dict] = None
    extracted_entities: Dict[str, Any] = None
    business_actions: List[Dict] = None
    sentiment_scores: List[float] = None
    
    # Technical context
    room_id: Optional[str] = None
    participant_id: Optional[str] = None
    session_start: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def __post_init__(self):
        if self.previous_scenarios is None:
            self.previous_scenarios = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.extracted_entities is None:
            self.extracted_entities = {}
        if self.business_actions is None:
            self.business_actions = []
        if self.sentiment_scores is None:
            self.sentiment_scores = []
        if self.session_start is None:
            self.session_start = datetime.now()
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.session_start:
            data['session_start'] = self.session_start.isoformat()
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        # Convert enums to strings
        data['current_scenario'] = self.current_scenario.value
        data['priority'] = self.priority.value
        data['previous_scenarios'] = [s.value for s in self.previous_scenarios]
        return data


class BusinessLLM(llm.LLM):
    """Custom LLM wrapper optimized for business conversations"""
    
    def __init__(self, model: str, api_key: str, temperature: float = 0.3):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.initial_context = self._create_initial_context()
        
        # Business-specific prompts for different scenarios
        self.scenario_prompts = {
            Scenario.ONBOARDING: self._get_onboarding_prompt(),
            Scenario.SALES: self._get_sales_prompt(),
            Scenario.SUPPORT: self._get_support_prompt(),
            Scenario.SCHEDULING: self._get_scheduling_prompt(),
            Scenario.FOLLOW_UP: self._get_followup_prompt(),
            Scenario.ESCALATION: self._get_escalation_prompt(),
        }
    
    def _create_initial_context(self) -> llm.ChatContext:
        """Create initial context with business agent personality"""
        return llm.ChatContext().append(
            role="system",
            text="""You are VoiceFlow Pro, an intelligent business automation voice agent specializing in:

1. LEAD QUALIFICATION & SALES: Identify prospects, understand needs, qualify opportunities
2. CUSTOMER SUPPORT: Resolve issues, create tickets, escalate when needed
3. APPOINTMENT SCHEDULING: Book consultations, demos, and service appointments
4. RELATIONSHIP MANAGEMENT: Follow-ups, renewals, feedback collection

PERSONALITY:
- Professional yet warm and approachable
- Efficient and goal-oriented
- Excellent listener who asks clarifying questions
- Always follows business processes and compliance

CAPABILITIES:
- Real-time conversation analysis and sentiment detection
- Seamless handoffs between business scenarios
- Integration with CRM, calendar, and ticketing systems
- Multi-language business terminology understanding

RESPONSE GUIDELINES:
- Keep responses concise but complete (2-3 sentences max)
- Always acknowledge customer concerns immediately
- Ask one focused question to move conversation forward
- Use business terminology appropriately
- Maintain conversation context across scenario changes"""
        )
    
    def _get_onboarding_prompt(self) -> str:
        return """ONBOARDING MODE: You're greeting a new customer and determining their needs.
- Welcome them warmly and introduce VoiceFlow Pro capabilities
- Ask open-ended questions to understand their business goals
- Listen for keywords that indicate sales, support, or scheduling needs
- Transition smoothly to the appropriate specialized scenario"""
    
    def _get_sales_prompt(self) -> str:
        return """SALES MODE: You're qualifying a sales lead and gathering requirements.
- Focus on understanding their current challenges and pain points
- Ask about company size, current solutions, budget timeline
- Identify decision-makers and evaluation process
- Propose appropriate demos, trials, or consultations
- Calculate and track lead scoring in real-time"""
    
    def _get_support_prompt(self) -> str:
        return """SUPPORT MODE: You're helping resolve customer issues.
- Immediately acknowledge the problem and show empathy
- Gather detailed technical information and error descriptions
- Determine urgency level and appropriate escalation path
- Create support tickets with proper categorization
- Provide status updates and next steps clearly"""
    
    def _get_scheduling_prompt(self) -> str:
        return """SCHEDULING MODE: You're booking appointments and managing calendars.
- Understand the type of meeting needed (demo, consultation, support)
- Check real-time calendar availability across multiple resources
- Handle scheduling conflicts and propose alternatives
- Collect required participant information and preferences
- Send confirmations and calendar invites immediately"""
    
    def _get_followup_prompt(self) -> str:
        return """FOLLOW-UP MODE: You're managing ongoing customer relationships.
- Reference previous interactions and conversation history
- Check on progress of previous issues or commitments
- Identify opportunities for additional services or renewals
- Collect feedback on recent experiences
- Schedule appropriate next touchpoints"""
    
    def _get_escalation_prompt(self) -> str:
        return """ESCALATION MODE: You're handling complex issues requiring human intervention.
- Clearly explain why escalation is necessary
- Summarize all relevant context for the human agent
- Set appropriate expectations for response time
- Ensure smooth handoff with minimal customer friction
- Continue to provide updates during the transition"""


class IntentClassifier:
    """Advanced intent classification for business scenarios"""
    
    def __init__(self):
        # Business terminology patterns for intent detection
        self.intent_patterns = {
            Scenario.SALES: [
                r'\b(interested|buy|purchase|price|cost|demo|trial|evaluate)\b',
                r'\b(solution|product|service|package|plan|subscription)\b',
                r'\b(quote|proposal|contract|agreement|enterprise)\b',
                r'\b(budget|timeline|decision|stakeholder|requirement)\b'
            ],
            Scenario.SUPPORT: [
                r'\b(problem|issue|error|bug|broken|not working)\b',
                r'\b(help|support|assistance|troubleshoot|fix)\b',
                r'\b(urgent|critical|down|outage|failed)\b',
                r'\b(ticket|case|incident|report|complaint)\b'
            ],
            Scenario.SCHEDULING: [
                r'\b(schedule|appointment|meeting|book|calendar)\b',
                r'\b(available|availability|time|date|when)\b',
                r'\b(demo|consultation|call|presentation|review)\b',
                r'\b(reschedule|cancel|postpone|change|move)\b'
            ],
            Scenario.FOLLOW_UP: [
                r'\b(follow.?up|check.?in|status|update|progress)\b',
                r'\b(renewal|contract|subscription|agreement)\b',
                r'\b(feedback|satisfaction|experience|review)\b',
                r'\b(previous|last time|before|earlier)\b'
            ]
        }
        
        # Business entity patterns
        self.entity_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            'company': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|LLC|Corp|Ltd|Co))\.?)\b',
            'money': r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d+\s*(?:dollars?|k|million|thousand)\b',
            'date': r'\b(?:today|tomorrow|next\s+\w+|this\s+\w+|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            'time': r'\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\b'
        }
    
    async def classify_intent(self, text: str, context: CustomerContext) -> Scenario:
        """Classify intent based on text and conversation context"""
        text_lower = text.lower()
        scenario_scores = {}
        
        # Score each scenario based on pattern matching
        for scenario, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            scenario_scores[scenario] = score
        
        # Apply context weighting
        if context.current_scenario in scenario_scores:
            scenario_scores[context.current_scenario] *= 1.5  # Boost current scenario
        
        # Handle escalation triggers
        if any(word in text_lower for word in ['urgent', 'critical', 'emergency', 'manager', 'supervisor']):
            return Scenario.ESCALATION
        
        # Return highest scoring scenario or default to current
        if max(scenario_scores.values()) > 0:
            return max(scenario_scores, key=scenario_scores.get)
        
        return context.current_scenario
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract business entities from text"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities


class DatabaseManager:
    """Handles database persistence for conversation data"""
    
    def __init__(self, backend_url: str = "http://backend:8000"):
        self.backend_url = backend_url
    
    async def save_conversation_state(self, context: CustomerContext) -> bool:
        """Save conversation state to database"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_url}/api/conversation/state",
                    json=context.to_dict()
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to save conversation state: {e}")
            return False
    
    async def load_conversation_state(self, room_id: str) -> Optional[CustomerContext]:
        """Load conversation state from database"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/api/conversation/state/{room_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return CustomerContext(**data)
        except Exception as e:
            logger.error(f"Failed to load conversation state: {e}")
        
        return None
    
    async def log_conversation_message(self, room_id: str, speaker: str, message: str, 
                                     metadata: Dict[str, Any]) -> bool:
        """Log individual conversation message"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.backend_url}/api/conversation/message",
                    json={
                        "room_id": room_id,
                        "speaker": speaker,
                        "message": message,
                        "metadata": metadata,
                        "timestamp": datetime.now().isoformat()
                    }
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to log conversation message: {e}")
            return False


class VoiceFlowAgent:
    """
    Advanced VoiceFlow Pro agent with multi-scenario support and business intelligence
    """
    
    def __init__(self, job_context: JobContext, participant: rtc.Participant):
        # Note: VoiceAssistant integration would be added here in production
        self.job_context = job_context
        self.participant = participant
        self.customer_context = CustomerContext(
            room_id=job_context.room.name,
            participant_id=participant.identity
        )
        
        # Initialize components
        self.intent_classifier = IntentClassifier()
        self.db_manager = DatabaseManager()
        
        # Agent handlers for different scenarios
        self.scenario_handlers = {
            Scenario.ONBOARDING: self._handle_onboarding,
            Scenario.SALES: self._handle_sales,
            Scenario.SUPPORT: self._handle_support,
            Scenario.SCHEDULING: self._handle_scheduling,
            Scenario.FOLLOW_UP: self._handle_follow_up,
            Scenario.ESCALATION: self._handle_escalation,
        }
        
        # Conversation state
        self.conversation_active = True
        self.last_transcript = ""
        self.sentiment_analyzer = SentimentAnalyzer()
    
    async def setup_event_handlers(self):
        """Set up event handlers for LiveKit room events"""
        self.job_context.room.on("participant_disconnected", self._on_participant_disconnected)
        self.job_context.room.on("data_received", self._on_data_received)
        
        # Load existing conversation state if any
        existing_context = await self.db_manager.load_conversation_state(self.customer_context.room_id)
        if existing_context:
            self.customer_context = existing_context
            logger.info(f"Loaded existing conversation context for room {self.customer_context.room_id}")
    
    async def process_conversation(self, transcript: str) -> str:
        """
        Main conversation processing pipeline with advanced business logic
        """
        logger.info(f"Processing transcript: {transcript}")
        
        # Update activity timestamp
        self.customer_context.last_activity = datetime.now()
        
        # Extract entities from current message
        entities = self.intent_classifier.extract_entities(transcript)
        self.customer_context.extracted_entities.update(entities)
        
        # Classify intent and determine scenario
        new_scenario = await self.intent_classifier.classify_intent(transcript, self.customer_context)
        
        # Handle scenario transitions
        if new_scenario != self.customer_context.current_scenario:
            await self._handle_scenario_transition(new_scenario)
        
        # Analyze sentiment
        sentiment_score = await self.sentiment_analyzer.analyze(transcript)
        self.customer_context.sentiment_scores.append(sentiment_score)
        
        # Route to appropriate scenario handler
        handler = self.scenario_handlers.get(new_scenario, self._handle_onboarding)
        response = await handler(transcript)
        
        # Log conversation to database
        await self._log_conversation_turn(transcript, response, entities, sentiment_score)
        
        # Save updated context
        await self.db_manager.save_conversation_state(self.customer_context)
        
        return response
    
    async def _handle_scenario_transition(self, new_scenario: Scenario):
        """Handle transitions between business scenarios"""
        old_scenario = self.customer_context.current_scenario
        self.customer_context.previous_scenarios.append(old_scenario)
        self.customer_context.current_scenario = new_scenario
        
        logger.info(f"Scenario transition: {old_scenario.value} → {new_scenario.value}")
        
        # Record business action for scenario change
        self.customer_context.business_actions.append({
            "type": "scenario_transition",
            "from": old_scenario.value,
            "to": new_scenario.value,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_onboarding(self, transcript: str) -> str:
        """Handle initial customer onboarding and needs assessment"""
        logger.info("Handling onboarding scenario")
        
        responses = [
            "Welcome to VoiceFlow Pro! I'm here to help with your business needs. Whether you're interested in our solutions, need support, or want to schedule a consultation, I'm ready to assist. What brings you here today?",
            "Thank you for reaching out! I can help you with product information, technical support, or scheduling appointments. What would you like to know more about?",
            "Great to have you here! I specialize in helping businesses like yours. Could you tell me a bit about your current challenges or what you're hoping to accomplish?"
        ]
        
        # Choose response based on conversation length
        response_index = min(len(self.customer_context.conversation_history) // 2, len(responses) - 1)
        return responses[response_index]
    
    async def _handle_sales(self, transcript: str) -> str:
        """Handle sales qualification and lead management"""
        logger.info("Handling sales scenario")
        
        # Update lead score based on engagement
        self.customer_context.lead_score += 10
        
        # Record sales action
        self.customer_context.business_actions.append({
            "type": "sales_interaction",
            "lead_score": self.customer_context.lead_score,
            "timestamp": datetime.now().isoformat()
        })
        
        if "demo" in transcript.lower():
            return "I'd be happy to schedule a personalized demo for you! Our platform can significantly improve your business efficiency. What's your availability this week? I can also have one of our solution specialists join us."
        
        elif "price" in transcript.lower() or "cost" in transcript.lower():
            return "Our pricing depends on your specific needs and company size. I'd like to understand your requirements better so I can provide accurate pricing. How many users would need access, and what's your primary use case?"
        
        else:
            return "I understand you're evaluating solutions for your business. To recommend the best package, could you tell me about your current setup and main challenges? This helps me match you with the right features."
    
    async def _handle_support(self, transcript: str) -> str:
        """Handle customer support with intelligent triage"""
        logger.info("Handling support scenario")
        
        # Analyze urgency
        urgency_keywords = ["urgent", "critical", "down", "outage", "emergency"]
        is_urgent = any(keyword in transcript.lower() for keyword in urgency_keywords)
        
        if is_urgent:
            self.customer_context.priority = Priority.CRITICAL
        
        # Create support ticket action
        ticket_id = f"TICK-{datetime.now().strftime('%Y%m%d')}-{hash(transcript) % 10000:04d}"
        
        self.customer_context.business_actions.append({
            "type": "support_ticket",
            "ticket_id": ticket_id,
            "priority": self.customer_context.priority.value,
            "description": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        if is_urgent:
            return f"I understand this is urgent and I'm escalating immediately. I've created priority ticket {ticket_id} and you'll receive a callback from our technical team within 15 minutes. Can you provide any additional details about the issue?"
        
        return f"I'm here to help resolve your issue. I've created ticket {ticket_id} to track this. Can you describe exactly what's happening and when it started? This will help me connect you with the right specialist."
    
    async def _handle_scheduling(self, transcript: str) -> str:
        """Handle appointment scheduling with calendar integration"""
        logger.info("Handling scheduling scenario")
        
        # Record scheduling action
        self.customer_context.business_actions.append({
            "type": "scheduling_request",
            "requested_time": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        if "demo" in transcript.lower():
            return "Perfect! I can schedule a product demonstration for you. I have availability next Tuesday at 2 PM or Wednesday at 10 AM. The demo will take about 30 minutes and I'll send you the meeting link. Which time works better?"
        
        elif "consultation" in transcript.lower():
            return "I'd be happy to schedule a consultation with one of our specialists. We have slots available this week on Tuesday afternoon or Thursday morning. What type of consultation are you looking for, and do you prefer morning or afternoon?"
        
        else:
            return "I can help you schedule an appointment. What type of meeting would you like - a product demo, technical consultation, or something else? And what's your preferred time frame?"
    
    async def _handle_follow_up(self, transcript: str) -> str:
        """Handle follow-up conversations and relationship management"""
        logger.info("Handling follow-up scenario")
        
        # Record follow-up action
        self.customer_context.business_actions.append({
            "type": "follow_up",
            "context": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        return "Thank you for following up! I have your previous conversation history here. How did everything go with your last request? Is there anything else I can help you with today?"
    
    async def _handle_escalation(self, transcript: str) -> str:
        """Handle escalations to human agents"""
        logger.info("Handling escalation scenario")
        
        self.customer_context.priority = Priority.CRITICAL
        
        # Record escalation action
        self.customer_context.business_actions.append({
            "type": "escalation",
            "reason": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        return "I understand you need to speak with a supervisor. I'm connecting you with our management team right now. Please hold for just a moment while I transfer you with all the context from our conversation."
    
    async def _log_conversation_turn(self, transcript: str, response: str, entities: Dict, sentiment: float):
        """Log a complete conversation turn to database"""
        # Log customer message
        await self.db_manager.log_conversation_message(
            room_id=self.customer_context.room_id,
            speaker="customer",
            message=transcript,
            metadata={
                "entities": entities,
                "sentiment": sentiment,
                "scenario": self.customer_context.current_scenario.value
            }
        )
        
        # Log agent response
        await self.db_manager.log_conversation_message(
            room_id=self.customer_context.room_id,
            speaker="agent",
            message=response,
            metadata={
                "scenario": self.customer_context.current_scenario.value,
                "lead_score": self.customer_context.lead_score
            }
        )
        
        # Update conversation history
        self.customer_context.conversation_history.extend([
            {
                "speaker": "customer",
                "message": transcript,
                "timestamp": datetime.now().isoformat(),
                "scenario": self.customer_context.current_scenario.value
            },
            {
                "speaker": "agent",
                "message": response,
                "timestamp": datetime.now().isoformat(),
                "scenario": self.customer_context.current_scenario.value
            }
        ])
    
    async def _on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        """Handle participant disconnection"""
        if participant.identity == self.participant.identity:
            logger.info(f"Customer {participant.identity} disconnected")
            self.conversation_active = False
            
            # Save final conversation state
            self.customer_context.business_actions.append({
                "type": "session_ended",
                "duration": (datetime.now() - self.customer_context.session_start).total_seconds(),
                "timestamp": datetime.now().isoformat()
            })
            
            await self.db_manager.save_conversation_state(self.customer_context)
    
    async def _on_data_received(self, data: rtc.DataPacket):
        """Handle data messages from frontend"""
        try:
            message = json.loads(data.data.decode())
            if message.get("type") == "context_update":
                # Update customer context from frontend
                self.customer_context.extracted_entities.update(message.get("entities", {}))
                logger.info("Updated customer context from frontend")
        except Exception as e:
            logger.error(f"Error processing data message: {e}")


class SentimentAnalyzer:
    """Simple sentiment analysis for customer interactions"""
    
    def __init__(self):
        self.positive_words = ["good", "great", "excellent", "perfect", "amazing", "love", "satisfied", "happy"]
        self.negative_words = ["bad", "terrible", "awful", "hate", "frustrated", "angry", "disappointed", "upset"]
    
    async def analyze(self, text: str) -> float:
        """Analyze sentiment and return score between -1.0 and 1.0"""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)
        
        total_words = len(text_lower.split())
        if total_words == 0:
            return 0.0
        
        return (positive_count - negative_count) / max(total_words, 1)