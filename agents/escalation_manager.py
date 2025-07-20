"""
Escalation Management with Human Agent LiveKit Integration

This module provides sophisticated escalation management that:
- Detects escalation triggers in real-time
- Seamlessly brings human agents into LiveKit rooms
- Manages context handoff between AI and human agents
- Provides human agents with full conversation context
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
from livekit import rtc, api
from livekit.api import RoomServiceClient

from context_manager import AdvancedContextManager
from sentiment_analyzer import AdvancedSentimentAnalyzer, SentimentAnalysis, EmotionalState
from voice_agent import CustomerContext, Scenario, Priority

logger = logging.getLogger(__name__)


class EscalationType(Enum):
    """Types of escalation scenarios"""
    CUSTOMER_REQUEST = "customer_request"
    SENTIMENT_TRIGGERED = "sentiment_triggered"
    TECHNICAL_COMPLEXITY = "technical_complexity"
    SALES_OPPORTUNITY = "sales_opportunity"
    EMERGENCY = "emergency"
    COMPLIANCE = "compliance"
    VIP_CUSTOMER = "vip_customer"


class EscalationUrgency(Enum):
    """Urgency levels for escalations"""
    LOW = "low"          # 15+ minutes response time
    MEDIUM = "medium"    # 5-15 minutes response time  
    HIGH = "high"        # 1-5 minutes response time
    CRITICAL = "critical" # Immediate response required


class HumanAgentType(Enum):
    """Types of human agents available"""
    GENERAL_SUPPORT = "general_support"
    TECHNICAL_SPECIALIST = "technical_specialist"
    SALES_SPECIALIST = "sales_specialist"
    CUSTOMER_SUCCESS = "customer_success"
    SUPERVISOR = "supervisor"
    BILLING_SPECIALIST = "billing_specialist"
    COMPLIANCE_OFFICER = "compliance_officer"


@dataclass
class EscalationTrigger:
    """Escalation trigger detection result"""
    trigger_type: EscalationType
    urgency: EscalationUrgency
    confidence: float
    trigger_reason: str
    recommended_agent_type: HumanAgentType
    context_summary: str
    trigger_keywords: List[str]
    triggered_at: datetime


@dataclass
class HumanAgent:
    """Human agent information"""
    agent_id: str
    name: str
    agent_type: HumanAgentType
    specialties: List[str]
    current_load: int  # Number of active conversations
    max_capacity: int
    availability_status: str  # available, busy, away
    average_response_time: float  # in seconds
    customer_satisfaction_rating: float
    languages: List[str]
    last_active: datetime


@dataclass
class EscalationSession:
    """Active escalation session tracking"""
    escalation_id: str
    room_id: str
    customer_id: str
    ai_agent_id: str
    human_agent: Optional[HumanAgent]
    escalation_trigger: EscalationTrigger
    escalation_started: datetime
    human_joined: Optional[datetime]
    handoff_completed: Optional[datetime]
    session_status: str  # waiting, in_progress, completed, failed
    context_package: Dict[str, Any]
    conversation_summary: str
    resolution_notes: Optional[str]


class EscalationManager:
    """
    Advanced escalation management with LiveKit integration
    """
    
    def __init__(self, livekit_url: str, api_key: str, api_secret: str):
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        
        # LiveKit services
        self.room_service = RoomServiceClient(livekit_url, api_key, api_secret)
        
        # Context and sentiment services
        self.context_manager = AdvancedContextManager()
        self.sentiment_analyzer = AdvancedSentimentAnalyzer()
        
        # Escalation triggers and patterns
        self.escalation_patterns = {
            EscalationType.CUSTOMER_REQUEST: [
                r'\b(speak to|talk to|get me) (a )?(manager|supervisor|human|person)\b',
                r'\b(escalate|escalation|escalate this)\b',
                r'\b(transfer me|transfer to)\b',
                r'\b(this (isn\'t|is not) working|I need (a )?human)\b'
            ],
            EscalationType.EMERGENCY: [
                r'\b(emergency|urgent|critical|down|outage|broken)\b',
                r'\b(production (is )?down|system (is )?down)\b',
                r'\b(losing money|business critical|mission critical)\b',
                r'\b(security (breach|incident)|data (breach|loss))\b'
            ],
            EscalationType.COMPLIANCE: [
                r'\b(gdpr|hipaa|compliance|privacy|legal|lawsuit)\b',
                r'\b(data protection|personal data|sensitive information)\b',
                r'\b(audit|auditor|regulatory|regulation)\b'
            ]
        }
        
        # Agent routing logic
        self.agent_routing = {
            Scenario.SALES: [HumanAgentType.SALES_SPECIALIST, HumanAgentType.CUSTOMER_SUCCESS],
            Scenario.SUPPORT: [HumanAgentType.TECHNICAL_SPECIALIST, HumanAgentType.GENERAL_SUPPORT],
            Scenario.ESCALATION: [HumanAgentType.SUPERVISOR, HumanAgentType.CUSTOMER_SUCCESS]
        }
        
        # Mock human agent pool (in production, this would come from HR/staffing system)
        self.available_agents: Dict[str, HumanAgent] = {}
        self._initialize_agent_pool()
        
        # Active escalations tracking
        self.active_escalations: Dict[str, EscalationSession] = {}
        
        # Escalation metrics
        self.escalation_metrics = {
            "total_escalations": 0,
            "successful_handoffs": 0,
            "average_response_time": 0.0,
            "escalation_types": {}
        }
    
    def _initialize_agent_pool(self):
        """Initialize mock human agent pool"""
        agents = [
            HumanAgent(
                agent_id="agent_001",
                name="Sarah Chen",
                agent_type=HumanAgentType.TECHNICAL_SPECIALIST,
                specialties=["API integration", "System troubleshooting", "Database issues"],
                current_load=2,
                max_capacity=5,
                availability_status="available",
                average_response_time=120.0,
                customer_satisfaction_rating=4.8,
                languages=["English", "Mandarin"],
                last_active=datetime.now()
            ),
            HumanAgent(
                agent_id="agent_002", 
                name="Michael Rodriguez",
                agent_type=HumanAgentType.SALES_SPECIALIST,
                specialties=["Enterprise sales", "Custom solutions", "Pricing"],
                current_load=1,
                max_capacity=4,
                availability_status="available",
                average_response_time=90.0,
                customer_satisfaction_rating=4.9,
                languages=["English", "Spanish"],
                last_active=datetime.now()
            ),
            HumanAgent(
                agent_id="agent_003",
                name="Jennifer Kim",
                agent_type=HumanAgentType.SUPERVISOR,
                specialties=["Escalation management", "Customer relations", "Complex issues"],
                current_load=0,
                max_capacity=3,
                availability_status="available",
                average_response_time=60.0,
                customer_satisfaction_rating=4.9,
                languages=["English", "Korean"],
                last_active=datetime.now()
            )
        ]
        
        for agent in agents:
            self.available_agents[agent.agent_id] = agent
    
    async def detect_escalation_triggers(self, customer_context: CustomerContext,
                                       current_message: str,
                                       sentiment_analysis: SentimentAnalysis,
                                       conversation_history: List[Dict]) -> Optional[EscalationTrigger]:
        """
        Detect if escalation is needed based on multiple factors
        """
        
        # Check explicit customer requests
        explicit_trigger = self._check_explicit_escalation_request(current_message)
        if explicit_trigger:
            return explicit_trigger
        
        # Check sentiment-based triggers
        sentiment_trigger = self._check_sentiment_escalation(sentiment_analysis, conversation_history)
        if sentiment_trigger:
            return sentiment_trigger
        
        # Check conversation duration and complexity
        complexity_trigger = await self._check_complexity_escalation(
            customer_context, conversation_history
        )
        if complexity_trigger:
            return complexity_trigger
        
        # Check VIP customer status
        vip_trigger = await self._check_vip_escalation(customer_context)
        if vip_trigger:
            return vip_trigger
        
        # Check compliance triggers
        compliance_trigger = self._check_compliance_escalation(current_message)
        if compliance_trigger:
            return compliance_trigger
        
        return None
    
    def _check_explicit_escalation_request(self, message: str) -> Optional[EscalationTrigger]:
        """Check for explicit escalation requests"""
        message_lower = message.lower()
        
        for escalation_type, patterns in self.escalation_patterns.items():
            for pattern in patterns:
                import re
                if re.search(pattern, message_lower):
                    urgency = EscalationUrgency.HIGH if escalation_type == EscalationType.EMERGENCY else EscalationUrgency.MEDIUM
                    
                    return EscalationTrigger(
                        trigger_type=escalation_type,
                        urgency=urgency,
                        confidence=0.9,
                        trigger_reason=f"Customer explicitly requested: {pattern}",
                        recommended_agent_type=self._get_recommended_agent_type(escalation_type),
                        context_summary="Customer made explicit escalation request",
                        trigger_keywords=re.findall(pattern, message_lower),
                        triggered_at=datetime.now()
                    )
        
        return None
    
    def _check_sentiment_escalation(self, sentiment_analysis: SentimentAnalysis,
                                  conversation_history: List[Dict]) -> Optional[EscalationTrigger]:
        """Check for sentiment-based escalation triggers"""
        
        # High escalation risk
        if sentiment_analysis.escalation_risk > 0.8:
            return EscalationTrigger(
                trigger_type=EscalationType.SENTIMENT_TRIGGERED,
                urgency=EscalationUrgency.HIGH,
                confidence=sentiment_analysis.escalation_risk,
                trigger_reason=f"High escalation risk score: {sentiment_analysis.escalation_risk:.2f}",
                recommended_agent_type=HumanAgentType.SUPERVISOR,
                context_summary=f"Customer showing {sentiment_analysis.emotional_state.value} emotion",
                trigger_keywords=["sentiment_risk"],
                triggered_at=datetime.now()
            )
        
        # Persistent negative sentiment
        if len(conversation_history) >= 3:
            recent_sentiments = [turn.get('sentiment', 0) for turn in conversation_history[-3:]]
            if all(s < -0.3 for s in recent_sentiments):
                return EscalationTrigger(
                    trigger_type=EscalationType.SENTIMENT_TRIGGERED,
                    urgency=EscalationUrgency.MEDIUM,
                    confidence=0.8,
                    trigger_reason="Persistent negative sentiment over multiple turns",
                    recommended_agent_type=HumanAgentType.CUSTOMER_SUCCESS,
                    context_summary="Customer sentiment declining consistently",
                    trigger_keywords=["negative_trend"],
                    triggered_at=datetime.now()
                )
        
        return None
    
    async def _check_complexity_escalation(self, customer_context: CustomerContext,
                                         conversation_history: List[Dict]) -> Optional[EscalationTrigger]:
        """Check for complexity-based escalation"""
        
        # Long conversation without resolution
        if len(conversation_history) > 10:
            # Check if issue is still unresolved
            recent_messages = [turn.get('message', '') for turn in conversation_history[-5:]]
            repeated_issues = any('still' in msg.lower() or 'not working' in msg.lower() 
                                for msg in recent_messages)
            
            if repeated_issues:
                return EscalationTrigger(
                    trigger_type=EscalationType.TECHNICAL_COMPLEXITY,
                    urgency=EscalationUrgency.MEDIUM,
                    confidence=0.7,
                    trigger_reason="Long conversation without resolution",
                    recommended_agent_type=HumanAgentType.TECHNICAL_SPECIALIST,
                    context_summary="Complex technical issue requiring human expertise",
                    trigger_keywords=["unresolved", "complex"],
                    triggered_at=datetime.now()
                )
        
        return None
    
    async def _check_vip_escalation(self, customer_context: CustomerContext) -> Optional[EscalationTrigger]:
        """Check for VIP customer escalation"""
        
        # In production, this would check customer tier/value
        if customer_context.company and 'enterprise' in customer_context.company.lower():
            return EscalationTrigger(
                trigger_type=EscalationType.VIP_CUSTOMER,
                urgency=EscalationUrgency.HIGH,
                confidence=1.0,
                trigger_reason="VIP/Enterprise customer requires priority handling",
                recommended_agent_type=HumanAgentType.CUSTOMER_SUCCESS,
                context_summary="High-value customer requiring premium support",
                trigger_keywords=["vip", "enterprise"],
                triggered_at=datetime.now()
            )
        
        return None
    
    def _check_compliance_escalation(self, message: str) -> Optional[EscalationTrigger]:
        """Check for compliance-related escalation"""
        
        compliance_patterns = self.escalation_patterns.get(EscalationType.COMPLIANCE, [])
        message_lower = message.lower()
        
        for pattern in compliance_patterns:
            import re
            if re.search(pattern, message_lower):
                return EscalationTrigger(
                    trigger_type=EscalationType.COMPLIANCE,
                    urgency=EscalationUrgency.CRITICAL,
                    confidence=0.95,
                    trigger_reason="Compliance-related keywords detected",
                    recommended_agent_type=HumanAgentType.COMPLIANCE_OFFICER,
                    context_summary="Legal/compliance matter requiring immediate attention",
                    trigger_keywords=re.findall(pattern, message_lower),
                    triggered_at=datetime.now()
                )
        
        return None
    
    def _get_recommended_agent_type(self, escalation_type: EscalationType) -> HumanAgentType:
        """Get recommended human agent type for escalation"""
        
        agent_mapping = {
            EscalationType.CUSTOMER_REQUEST: HumanAgentType.GENERAL_SUPPORT,
            EscalationType.SENTIMENT_TRIGGERED: HumanAgentType.SUPERVISOR,
            EscalationType.TECHNICAL_COMPLEXITY: HumanAgentType.TECHNICAL_SPECIALIST,
            EscalationType.SALES_OPPORTUNITY: HumanAgentType.SALES_SPECIALIST,
            EscalationType.EMERGENCY: HumanAgentType.SUPERVISOR,
            EscalationType.COMPLIANCE: HumanAgentType.COMPLIANCE_OFFICER,
            EscalationType.VIP_CUSTOMER: HumanAgentType.CUSTOMER_SUCCESS
        }
        
        return agent_mapping.get(escalation_type, HumanAgentType.GENERAL_SUPPORT)
    
    async def initiate_escalation(self, customer_context: CustomerContext,
                                escalation_trigger: EscalationTrigger,
                                current_room_id: str) -> EscalationSession:
        """
        Initiate escalation process and bring human agent into room
        """
        
        escalation_id = f"esc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{customer_context.room_id}"
        
        logger.info(f"Initiating escalation {escalation_id} for {escalation_trigger.trigger_type.value}")
        
        # Prepare comprehensive context package
        context_package = await self._prepare_escalation_context(
            customer_context, escalation_trigger
        )
        
        # Find available human agent
        selected_agent = await self._select_human_agent(escalation_trigger)
        
        # Create escalation session
        escalation_session = EscalationSession(
            escalation_id=escalation_id,
            room_id=current_room_id,
            customer_id=customer_context.room_id,
            ai_agent_id="voiceflow_ai",
            human_agent=selected_agent,
            escalation_trigger=escalation_trigger,
            escalation_started=datetime.now(),
            human_joined=None,
            handoff_completed=None,
            session_status="waiting",
            context_package=context_package,
            conversation_summary=context_package.get('summary', ''),
            resolution_notes=None
        )
        
        # Store in active escalations
        self.active_escalations[escalation_id] = escalation_session
        
        if selected_agent:
            # Invite human agent to LiveKit room
            await self._invite_human_agent_to_room(current_room_id, selected_agent, context_package)
            escalation_session.session_status = "in_progress"
        else:
            # Queue escalation for when agent becomes available
            await self._queue_escalation(escalation_session)
            escalation_session.session_status = "queued"
        
        # Update metrics
        self._update_escalation_metrics(escalation_trigger)
        
        return escalation_session
    
    async def _prepare_escalation_context(self, customer_context: CustomerContext,
                                        escalation_trigger: EscalationTrigger) -> Dict[str, Any]:
        """Prepare comprehensive context package for human agent"""
        
        # Get full conversation context
        full_context = await self.context_manager.build_comprehensive_context(
            customer_context.room_id, customer_context.participant_id
        )
        
        # Create executive summary
        summary = await self._create_escalation_summary(
            customer_context, escalation_trigger, full_context
        )
        
        context_package = {
            "escalation_info": {
                "trigger_type": escalation_trigger.trigger_type.value,
                "urgency": escalation_trigger.urgency.value,
                "trigger_reason": escalation_trigger.trigger_reason,
                "confidence": escalation_trigger.confidence
            },
            "customer_info": {
                "name": customer_context.name,
                "email": customer_context.email,
                "company": customer_context.company,
                "phone": customer_context.phone,
                "current_scenario": customer_context.current_scenario.value,
                "lead_score": customer_context.lead_score,
                "priority": customer_context.priority.value
            },
            "conversation_context": full_context,
            "summary": summary,
            "recommended_actions": self._generate_recommended_actions(escalation_trigger),
            "escalation_time": datetime.now().isoformat(),
            "ai_agent_notes": "Customer escalated from AI agent conversation"
        }
        
        return context_package
    
    async def _create_escalation_summary(self, customer_context: CustomerContext,
                                       escalation_trigger: EscalationTrigger,
                                       full_context: Dict[str, Any]) -> str:
        """Create executive summary for human agent"""
        
        summary_parts = [
            f"ESCALATION SUMMARY - {escalation_trigger.trigger_type.value.upper()}",
            f"Customer: {customer_context.name or 'Unknown'} ({customer_context.company or 'No company'})",
            f"Trigger: {escalation_trigger.trigger_reason}",
            f"Urgency: {escalation_trigger.urgency.value.upper()}",
            ""
        ]
        
        # Add conversation highlights
        contexts = full_context.get('context_layers', {})
        if 'short_term' in contexts:
            short_term = contexts['short_term']
            summary_parts.extend([
                "CURRENT SESSION:",
                f"- {short_term.get('session_summary', 'No summary available')}",
                ""
            ])
        
        # Add key issues
        if escalation_trigger.trigger_keywords:
            summary_parts.extend([
                "KEY ISSUES:",
                f"- {', '.join(escalation_trigger.trigger_keywords)}",
                ""
            ])
        
        # Add recommended next steps
        summary_parts.extend([
            "RECOMMENDED ACTIONS:",
            *[f"- {action}" for action in self._generate_recommended_actions(escalation_trigger)],
            ""
        ])
        
        return "\n".join(summary_parts)
    
    def _generate_recommended_actions(self, escalation_trigger: EscalationTrigger) -> List[str]:
        """Generate recommended actions for human agent"""
        
        base_actions = [
            "Review full conversation context",
            "Acknowledge escalation and apologize for any inconvenience",
            "Confirm understanding of customer's primary concern"
        ]
        
        trigger_specific_actions = {
            EscalationType.CUSTOMER_REQUEST: [
                "Thank customer for patience with AI interaction",
                "Provide direct human contact for future issues"
            ],
            EscalationType.SENTIMENT_TRIGGERED: [
                "Address emotional concerns first",
                "Show empathy and understanding",
                "Offer compensation if appropriate"
            ],
            EscalationType.TECHNICAL_COMPLEXITY: [
                "Review technical details with specialist",
                "Prepare screen sharing for troubleshooting",
                "Have development team on standby"
            ],
            EscalationType.EMERGENCY: [
                "Treat as P1 incident",
                "Engage emergency response team",
                "Provide hourly updates until resolved"
            ],
            EscalationType.COMPLIANCE: [
                "Involve legal/compliance team immediately",
                "Document all communications",
                "Follow regulatory escalation procedures"
            ]
        }
        
        specific_actions = trigger_specific_actions.get(escalation_trigger.trigger_type, [])
        return base_actions + specific_actions
    
    async def _select_human_agent(self, escalation_trigger: EscalationTrigger) -> Optional[HumanAgent]:
        """Select best available human agent for escalation"""
        
        # Filter agents by type
        suitable_agents = [
            agent for agent in self.available_agents.values()
            if agent.agent_type == escalation_trigger.recommended_agent_type
            and agent.availability_status == "available"
            and agent.current_load < agent.max_capacity
        ]
        
        # If no agents of preferred type, expand search
        if not suitable_agents:
            suitable_agents = [
                agent for agent in self.available_agents.values()
                if agent.availability_status == "available"
                and agent.current_load < agent.max_capacity
            ]
        
        # Select best agent based on load and rating
        if suitable_agents:
            # Score agents: lower load and higher rating is better
            def agent_score(agent: HumanAgent) -> float:
                load_score = 1.0 - (agent.current_load / agent.max_capacity)
                rating_score = agent.customer_satisfaction_rating / 5.0
                response_score = 1.0 - min(agent.average_response_time / 300.0, 1.0)  # 5 min max
                
                return (load_score * 0.4 + rating_score * 0.4 + response_score * 0.2)
            
            best_agent = max(suitable_agents, key=agent_score)
            
            # Update agent load
            best_agent.current_load += 1
            
            return best_agent
        
        return None
    
    async def _invite_human_agent_to_room(self, room_id: str, agent: HumanAgent, 
                                        context_package: Dict[str, Any]):
        """Invite human agent to LiveKit room with context"""
        
        try:
            # Create access token for human agent
            from livekit.api import AccessToken, VideoGrants
            
            token = AccessToken(self.api_key, self.api_secret)
            token.with_identity(f"human_agent_{agent.agent_id}")
            token.with_name(agent.name)
            token.with_grants(VideoGrants(
                room_join=True,
                room=room_id,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))
            token.with_metadata(json.dumps({
                "agent_type": "human",
                "agent_id": agent.agent_id,
                "specialties": agent.specialties,
                "escalation_context": context_package
            }))
            
            jwt_token = token.to_jwt()
            
            # Notify human agent (in production, this would integrate with agent dashboard)
            await self._notify_human_agent(agent, room_id, jwt_token, context_package)
            
            logger.info(f"Invited human agent {agent.name} to room {room_id}")
            
        except Exception as e:
            logger.error(f"Failed to invite human agent to room: {e}")
    
    async def _notify_human_agent(self, agent: HumanAgent, room_id: str, 
                                token: str, context_package: Dict[str, Any]):
        """Notify human agent of escalation (integration point for agent dashboard)"""
        
        # In production, this would send notification to agent dashboard/mobile app
        notification_payload = {
            "agent_id": agent.agent_id,
            "escalation_type": "voice_escalation",
            "room_id": room_id,
            "access_token": token,
            "urgency": context_package["escalation_info"]["urgency"],
            "customer_info": context_package["customer_info"],
            "summary": context_package["summary"],
            "livekit_url": self.livekit_url
        }
        
        # Mock notification (in production, send to agent notification system)
        logger.info(f"AGENT NOTIFICATION: {agent.name} - New escalation in room {room_id}")
        logger.info(f"Summary: {context_package['summary'][:200]}...")
    
    async def _queue_escalation(self, escalation_session: EscalationSession):
        """Queue escalation when no agents available"""
        
        # In production, this would integrate with queue management system
        logger.warning(f"No agents available - queuing escalation {escalation_session.escalation_id}")
        
        # Update customer with wait time estimate
        await self._send_queue_notification(escalation_session)
    
    async def _send_queue_notification(self, escalation_session: EscalationSession):
        """Send queue notification to customer"""
        
        # In production, this would send data message to customer in LiveKit room
        queue_message = {
            "type": "escalation_queued",
            "message": "I'm connecting you with a human specialist. Please hold for just a moment.",
            "estimated_wait_time": "2-3 minutes",
            "queue_position": 1
        }
        
        logger.info(f"Queue notification for escalation {escalation_session.escalation_id}")
    
    def _update_escalation_metrics(self, escalation_trigger: EscalationTrigger):
        """Update escalation metrics for reporting"""
        
        self.escalation_metrics["total_escalations"] += 1
        
        trigger_type = escalation_trigger.trigger_type.value
        if trigger_type not in self.escalation_metrics["escalation_types"]:
            self.escalation_metrics["escalation_types"][trigger_type] = 0
        self.escalation_metrics["escalation_types"][trigger_type] += 1
    
    async def handle_human_agent_joined(self, room_id: str, participant_identity: str):
        """Handle human agent joining the room"""
        
        if participant_identity.startswith("human_agent_"):
            agent_id = participant_identity.replace("human_agent_", "")
            
            # Find the escalation session
            escalation_session = None
            for session in self.active_escalations.values():
                if (session.room_id == room_id and 
                    session.human_agent and 
                    session.human_agent.agent_id == agent_id):
                    escalation_session = session
                    break
            
            if escalation_session:
                escalation_session.human_joined = datetime.now()
                escalation_session.session_status = "human_active"
                
                # Send handoff context to human agent
                await self._send_handoff_context(room_id, escalation_session)
                
                logger.info(f"Human agent joined escalation {escalation_session.escalation_id}")
    
    async def _send_handoff_context(self, room_id: str, escalation_session: EscalationSession):
        """Send context information to human agent via data channel"""
        
        handoff_data = {
            "type": "escalation_handoff",
            "escalation_id": escalation_session.escalation_id,
            "context_package": escalation_session.context_package,
            "ai_agent_notes": "Customer conversation history and context available",
            "recommended_actions": self._generate_recommended_actions(escalation_session.escalation_trigger)
        }
        
        # In production, send via LiveKit data channel to human agent
        logger.info(f"Sent handoff context for escalation {escalation_session.escalation_id}")
    
    async def complete_escalation(self, escalation_id: str, resolution_notes: str):
        """Mark escalation as completed"""
        
        if escalation_id in self.active_escalations:
            escalation_session = self.active_escalations[escalation_id]
            escalation_session.handoff_completed = datetime.now()
            escalation_session.session_status = "completed"
            escalation_session.resolution_notes = resolution_notes
            
            # Update agent load
            if escalation_session.human_agent:
                escalation_session.human_agent.current_load -= 1
            
            # Update metrics
            self.escalation_metrics["successful_handoffs"] += 1
            
            # Calculate response time
            if escalation_session.human_joined:
                response_time = (escalation_session.human_joined - escalation_session.escalation_started).total_seconds()
                current_avg = self.escalation_metrics["average_response_time"]
                total_escalations = self.escalation_metrics["successful_handoffs"]
                self.escalation_metrics["average_response_time"] = (
                    (current_avg * (total_escalations - 1) + response_time) / total_escalations
                )
            
            logger.info(f"Escalation {escalation_id} completed successfully")
            
            # Remove from active escalations after a delay (for reporting)
            asyncio.create_task(self._archive_escalation(escalation_id))
    
    async def _archive_escalation(self, escalation_id: str):
        """Archive completed escalation after delay"""
        await asyncio.sleep(300)  # 5 minutes
        if escalation_id in self.active_escalations:
            del self.active_escalations[escalation_id]
    
    def get_escalation_metrics(self) -> Dict[str, Any]:
        """Get escalation metrics for dashboard"""
        
        active_count = len([s for s in self.active_escalations.values() if s.session_status != "completed"])
        
        return {
            "total_escalations": self.escalation_metrics["total_escalations"],
            "successful_handoffs": self.escalation_metrics["successful_handoffs"],
            "average_response_time": self.escalation_metrics["average_response_time"],
            "escalation_types": self.escalation_metrics["escalation_types"],
            "active_escalations": active_count,
            "available_agents": len([a for a in self.available_agents.values() if a.availability_status == "available"])
        }