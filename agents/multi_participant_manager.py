"""
Multi-Participant Business Call Management for VoiceFlow Pro

This module enables sophisticated multi-participant calls including:
- 3-way calls with customer, AI agent, and human specialist
- Dynamic participant management and role assignment
- Context sharing across all participants
- Seamless handoffs between specialists
- Real-time collaboration features
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid
from livekit import rtc, api
from livekit.api import RoomServiceClient, ParticipantInfo

from escalation_manager import HumanAgent, HumanAgentType
from context_manager import AdvancedContextManager
from voice_agent import CustomerContext, Scenario

logger = logging.getLogger(__name__)


class ParticipantRole(Enum):
    """Roles for call participants"""
    CUSTOMER = "customer"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"
    SPECIALIST = "specialist"
    SUPERVISOR = "supervisor"
    OBSERVER = "observer"


class CallType(Enum):
    """Types of multi-participant calls"""
    TECHNICAL_CONSULTATION = "technical_consultation"
    SALES_DEMO = "sales_demo"
    ESCALATION_REVIEW = "escalation_review"
    TRAINING_SESSION = "training_session"
    EXPERT_CONSULTATION = "expert_consultation"
    MULTI_DEPARTMENT = "multi_department"


class ParticipantStatus(Enum):
    """Participant connection status"""
    INVITED = "invited"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SPEAKING = "speaking"
    MUTED = "muted"
    DISCONNECTED = "disconnected"


@dataclass
class CallParticipant:
    """Information about a call participant"""
    participant_id: str
    display_name: str
    role: ParticipantRole
    agent_type: Optional[HumanAgentType]
    specialties: List[str]
    status: ParticipantStatus
    join_time: Optional[datetime]
    speaking_time: float  # Total speaking time in seconds
    last_activity: Optional[datetime]
    permissions: Dict[str, bool]  # Can speak, share screen, etc.
    context_access_level: str  # full, limited, none


@dataclass
class MultiParticipantCall:
    """Multi-participant call session"""
    call_id: str
    room_id: str
    call_type: CallType
    primary_customer: str
    ai_agent_id: str
    participants: Dict[str, CallParticipant]
    call_purpose: str
    started_at: datetime
    expected_duration: int  # minutes
    current_speaker: Optional[str]
    conversation_context: Dict[str, Any]
    shared_documents: List[str]
    action_items: List[Dict[str, Any]]
    call_status: str  # active, on_hold, completed
    recording_enabled: bool


class MultiParticipantManager:
    """
    Advanced multi-participant call management with LiveKit
    """
    
    def __init__(self, livekit_url: str, api_key: str, api_secret: str):
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        
        # LiveKit services
        self.room_service = RoomServiceClient(livekit_url, api_key, api_secret)
        
        # Context manager
        self.context_manager = AdvancedContextManager()
        
        # Active calls
        self.active_calls: Dict[str, MultiParticipantCall] = {}
        
        # Available specialists
        self.available_specialists = self._initialize_specialist_pool()
        
        # Call templates for different scenarios
        self.call_templates = {
            CallType.TECHNICAL_CONSULTATION: {
                "required_roles": [ParticipantRole.CUSTOMER, ParticipantRole.AI_AGENT, ParticipantRole.SPECIALIST],
                "specialist_types": [HumanAgentType.TECHNICAL_SPECIALIST],
                "expected_duration": 30,
                "recording_recommended": True
            },
            CallType.SALES_DEMO: {
                "required_roles": [ParticipantRole.CUSTOMER, ParticipantRole.AI_AGENT, ParticipantRole.SPECIALIST],
                "specialist_types": [HumanAgentType.SALES_SPECIALIST, HumanAgentType.CUSTOMER_SUCCESS],
                "expected_duration": 45,
                "recording_recommended": True
            },
            CallType.ESCALATION_REVIEW: {
                "required_roles": [ParticipantRole.CUSTOMER, ParticipantRole.AI_AGENT, ParticipantRole.SUPERVISOR],
                "specialist_types": [HumanAgentType.SUPERVISOR, HumanAgentType.CUSTOMER_SUCCESS],
                "expected_duration": 20,
                "recording_recommended": True
            }
        }
        
        # Permission templates
        self.permission_templates = {
            ParticipantRole.CUSTOMER: {
                "can_speak": True,
                "can_mute_self": True,
                "can_share_screen": False,
                "can_invite_others": False,
                "can_end_call": False,
                "can_access_controls": False
            },
            ParticipantRole.AI_AGENT: {
                "can_speak": True,
                "can_mute_self": False,
                "can_share_screen": False,
                "can_invite_others": True,
                "can_end_call": False,
                "can_access_controls": True
            },
            ParticipantRole.SPECIALIST: {
                "can_speak": True,
                "can_mute_self": True,
                "can_share_screen": True,
                "can_invite_others": True,
                "can_end_call": True,
                "can_access_controls": True
            },
            ParticipantRole.SUPERVISOR: {
                "can_speak": True,
                "can_mute_self": True,
                "can_share_screen": True,
                "can_invite_others": True,
                "can_end_call": True,
                "can_access_controls": True
            }
        }
    
    def _initialize_specialist_pool(self) -> Dict[str, HumanAgent]:
        """Initialize pool of available specialists"""
        specialists = {
            "tech_001": HumanAgent(
                agent_id="tech_001",
                name="Dr. Alex Chen",
                agent_type=HumanAgentType.TECHNICAL_SPECIALIST,
                specialties=["API Integration", "System Architecture", "Performance Optimization"],
                current_load=0,
                max_capacity=3,
                availability_status="available",
                average_response_time=45.0,
                customer_satisfaction_rating=4.9,
                languages=["English", "Mandarin"],
                last_active=datetime.now()
            ),
            "sales_001": HumanAgent(
                agent_id="sales_001",
                name="Maria Rodriguez",
                agent_type=HumanAgentType.SALES_SPECIALIST,
                specialties=["Enterprise Sales", "Solution Architecture", "ROI Analysis"],
                current_load=1,
                max_capacity=4,
                availability_status="available",
                average_response_time=30.0,
                customer_satisfaction_rating=4.8,
                languages=["English", "Spanish"],
                last_active=datetime.now()
            ),
            "cs_001": HumanAgent(
                agent_id="cs_001",
                name="Jennifer Kim",
                agent_type=HumanAgentType.CUSTOMER_SUCCESS,
                specialties=["Onboarding", "Training", "Account Management"],
                current_load=0,
                max_capacity=5,
                availability_status="available",
                average_response_time=60.0,
                customer_satisfaction_rating=4.9,
                languages=["English", "Korean"],
                last_active=datetime.now()
            )
        }
        return specialists
    
    async def initiate_multi_participant_call(self, 
                                            customer_context: CustomerContext,
                                            call_type: CallType,
                                            call_purpose: str,
                                            requested_specialists: List[HumanAgentType] = None) -> MultiParticipantCall:
        """
        Initiate a multi-participant business call
        """
        call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Initiating {call_type.value} call {call_id}")
        
        # Get call template
        template = self.call_templates.get(call_type, {})
        
        # Create room for the call
        room_name = f"multiparty_{call_id}"
        await self._create_multiparty_room(room_name)
        
        # Prepare conversation context
        conversation_context = await self.context_manager.build_comprehensive_context(
            customer_context.room_id, customer_context.participant_id
        )
        
        # Create call session
        call_session = MultiParticipantCall(
            call_id=call_id,
            room_id=room_name,
            call_type=call_type,
            primary_customer=customer_context.participant_id,
            ai_agent_id="voiceflow_ai",
            participants={},
            call_purpose=call_purpose,
            started_at=datetime.now(),
            expected_duration=template.get("expected_duration", 30),
            current_speaker=None,
            conversation_context=conversation_context,
            shared_documents=[],
            action_items=[],
            call_status="active",
            recording_enabled=template.get("recording_recommended", False)
        )
        
        # Add customer as first participant
        await self._add_participant_to_call(
            call_session, 
            customer_context.participant_id,
            customer_context.name or "Customer",
            ParticipantRole.CUSTOMER
        )
        
        # Add AI agent
        await self._add_participant_to_call(
            call_session,
            "voiceflow_ai",
            "VoiceFlow Pro",
            ParticipantRole.AI_AGENT
        )
        
        # Add required specialists
        specialist_types = requested_specialists or template.get("specialist_types", [])
        for specialist_type in specialist_types:
            specialist = await self._find_available_specialist(specialist_type)
            if specialist:
                await self._add_participant_to_call(
                    call_session,
                    specialist.agent_id,
                    specialist.name,
                    ParticipantRole.SPECIALIST,
                    specialist.agent_type,
                    specialist.specialties
                )
                
                # Invite specialist to join
                await self._invite_specialist_to_call(call_session, specialist)
        
        # Store active call
        self.active_calls[call_id] = call_session
        
        # Start call recording if enabled
        if call_session.recording_enabled:
            await self._start_call_recording(call_session)
        
        return call_session
    
    async def _create_multiparty_room(self, room_name: str):
        """Create LiveKit room optimized for multi-participant calls"""
        try:
            room_config = api.CreateRoomRequest(
                name=room_name,
                empty_timeout=30 * 60,  # 30 minutes
                max_participants=10,
                metadata=json.dumps({
                    "call_type": "multi_participant",
                    "audio_preset": "conference",
                    "video_quality": "medium"
                })
            )
            
            await self.room_service.create_room(room_config)
            logger.info(f"Created multi-participant room: {room_name}")
            
        except Exception as e:
            logger.error(f"Failed to create multi-participant room: {e}")
            raise
    
    async def _add_participant_to_call(self, call_session: MultiParticipantCall,
                                     participant_id: str, display_name: str,
                                     role: ParticipantRole,
                                     agent_type: HumanAgentType = None,
                                     specialties: List[str] = None):
        """Add participant to call session"""
        
        permissions = self.permission_templates.get(role, {})
        
        participant = CallParticipant(
            participant_id=participant_id,
            display_name=display_name,
            role=role,
            agent_type=agent_type,
            specialties=specialties or [],
            status=ParticipantStatus.INVITED,
            join_time=None,
            speaking_time=0.0,
            last_activity=None,
            permissions=permissions,
            context_access_level="full" if role in [ParticipantRole.AI_AGENT, ParticipantRole.SPECIALIST] else "limited"
        )
        
        call_session.participants[participant_id] = participant
        
        logger.info(f"Added {role.value} {display_name} to call {call_session.call_id}")
    
    async def _find_available_specialist(self, specialist_type: HumanAgentType) -> Optional[HumanAgent]:
        """Find available specialist of specified type"""
        
        available_specialists = [
            specialist for specialist in self.available_specialists.values()
            if (specialist.agent_type == specialist_type and
                specialist.availability_status == "available" and
                specialist.current_load < specialist.max_capacity)
        ]
        
        if available_specialists:
            # Select best specialist based on load and rating
            def specialist_score(specialist: HumanAgent) -> float:
                load_score = 1.0 - (specialist.current_load / specialist.max_capacity)
                rating_score = specialist.customer_satisfaction_rating / 5.0
                return (load_score * 0.6 + rating_score * 0.4)
            
            best_specialist = max(available_specialists, key=specialist_score)
            best_specialist.current_load += 1
            return best_specialist
        
        return None
    
    async def _invite_specialist_to_call(self, call_session: MultiParticipantCall,
                                       specialist: HumanAgent):
        """Invite specialist to join the call"""
        
        # Create access token for specialist
        from livekit.api import AccessToken, VideoGrants
        
        token = AccessToken(self.api_key, self.api_secret)
        token.with_identity(specialist.agent_id)
        token.with_name(specialist.name)
        token.with_grants(VideoGrants(
            room_join=True,
            room=call_session.room_id,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        ))
        token.with_metadata(json.dumps({
            "role": "specialist",
            "call_id": call_session.call_id,
            "specialties": specialist.specialties,
            "context_access": "full"
        }))
        
        jwt_token = token.to_jwt()
        
        # Send invitation (in production, integrate with specialist notification system)
        invitation = {
            "specialist_id": specialist.agent_id,
            "call_id": call_session.call_id,
            "call_type": call_session.call_type.value,
            "call_purpose": call_session.call_purpose,
            "room_id": call_session.room_id,
            "access_token": jwt_token,
            "customer_context": call_session.conversation_context.get("customer_info", {}),
            "expected_duration": call_session.expected_duration,
            "livekit_url": self.livekit_url
        }
        
        logger.info(f"Invited specialist {specialist.name} to call {call_session.call_id}")
        
        # In production, send to specialist dashboard/mobile app
        await self._send_specialist_invitation(invitation)
    
    async def _send_specialist_invitation(self, invitation: Dict[str, Any]):
        """Send invitation to specialist (integration point)"""
        
        # Mock invitation sending
        logger.info(f"SPECIALIST INVITATION: {invitation['specialist_id']}")
        logger.info(f"Call: {invitation['call_purpose']}")
        logger.info(f"Duration: {invitation['expected_duration']} minutes")
    
    async def handle_participant_joined(self, call_id: str, participant_identity: str):
        """Handle participant joining the call"""
        
        if call_id not in self.active_calls:
            return
        
        call_session = self.active_calls[call_id]
        
        if participant_identity in call_session.participants:
            participant = call_session.participants[participant_identity]
            participant.status = ParticipantStatus.CONNECTED
            participant.join_time = datetime.now()
            participant.last_activity = datetime.now()
            
            logger.info(f"Participant {participant.display_name} joined call {call_id}")
            
            # Send welcome message and context
            await self._send_participant_welcome(call_session, participant)
            
            # Update call status if all required participants are present
            await self._check_call_readiness(call_session)
    
    async def _send_participant_welcome(self, call_session: MultiParticipantCall,
                                      participant: CallParticipant):
        """Send welcome message and context to new participant"""
        
        welcome_data = {
            "type": "participant_welcome",
            "call_id": call_session.call_id,
            "call_purpose": call_session.call_purpose,
            "your_role": participant.role.value,
            "permissions": participant.permissions,
            "other_participants": [
                {
                    "name": p.display_name,
                    "role": p.role.value,
                    "status": p.status.value
                }
                for p in call_session.participants.values()
                if p.participant_id != participant.participant_id
            ],
            "context_summary": self._generate_context_summary(call_session, participant),
            "expected_duration": call_session.expected_duration
        }
        
        # In production, send via LiveKit data channel
        logger.info(f"Sent welcome package to {participant.display_name}")
    
    def _generate_context_summary(self, call_session: MultiParticipantCall,
                                participant: CallParticipant) -> str:
        """Generate context summary appropriate for participant's access level"""
        
        context = call_session.conversation_context
        
        if participant.context_access_level == "full":
            # Full context for specialists and AI agents
            summary_parts = [
                f"Call Purpose: {call_session.call_purpose}",
                f"Customer: {context.get('customer_info', {}).get('name', 'Unknown')}",
                f"Company: {context.get('customer_info', {}).get('company', 'Unknown')}",
                f"Current Scenario: {context.get('customer_info', {}).get('current_scenario', 'Unknown')}",
                ""
            ]
            
            # Add conversation highlights
            if 'context_layers' in context and 'short_term' in context['context_layers']:
                short_term = context['context_layers']['short_term']
                summary_parts.extend([
                    "Recent Conversation:",
                    f"- {short_term.get('session_summary', 'No summary available')}",
                    ""
                ])
            
            return "\n".join(summary_parts)
        
        else:
            # Limited context for customers and observers
            return f"Multi-participant call: {call_session.call_purpose}"
    
    async def _check_call_readiness(self, call_session: MultiParticipantCall):
        """Check if call is ready to proceed with all required participants"""
        
        template = self.call_templates.get(call_session.call_type, {})
        required_roles = template.get("required_roles", [])
        
        connected_roles = [
            p.role for p in call_session.participants.values()
            if p.status == ParticipantStatus.CONNECTED
        ]
        
        all_required_present = all(role in connected_roles for role in required_roles)
        
        if all_required_present and call_session.call_status == "active":
            # All required participants present - start structured conversation
            await self._start_structured_conversation(call_session)
    
    async def _start_structured_conversation(self, call_session: MultiParticipantCall):
        """Start structured conversation flow for the call"""
        
        # Send conversation starter to all participants
        conversation_starter = {
            "type": "conversation_start",
            "call_id": call_session.call_id,
            "message": self._generate_conversation_opener(call_session),
            "speaking_order": self._determine_initial_speaking_order(call_session),
            "time_allocation": self._calculate_time_allocation(call_session)
        }
        
        logger.info(f"Started structured conversation for call {call_session.call_id}")
        
        # In production, send to all participants via data channel
        await self._broadcast_to_participants(call_session, conversation_starter)
    
    def _generate_conversation_opener(self, call_session: MultiParticipantCall) -> str:
        """Generate appropriate conversation opener"""
        
        openers = {
            CallType.TECHNICAL_CONSULTATION: f"Thank you all for joining this technical consultation about {call_session.call_purpose}. Let's start by reviewing the current situation and then discuss the best technical approach.",
            
            CallType.SALES_DEMO: f"Welcome everyone to this product demonstration for {call_session.call_purpose}. We'll show you how our solution addresses your specific requirements and discuss implementation options.",
            
            CallType.ESCALATION_REVIEW: f"Thank you for joining this escalation review regarding {call_session.call_purpose}. Our priority is understanding your concerns and finding an immediate resolution.",
            
            CallType.EXPERT_CONSULTATION: f"Welcome to this expert consultation on {call_session.call_purpose}. Our specialist will provide detailed insights and recommendations based on your specific needs."
        }
        
        return openers.get(call_session.call_type, f"Welcome to this call about {call_session.call_purpose}. Let's discuss how we can help you achieve your goals.")
    
    def _determine_initial_speaking_order(self, call_session: MultiParticipantCall) -> List[str]:
        """Determine optimal speaking order for participants"""
        
        # Standard order: AI Agent introduction, Customer needs, Specialist expertise
        order = []
        
        # AI agent starts
        ai_agents = [p.participant_id for p in call_session.participants.values() 
                    if p.role == ParticipantRole.AI_AGENT]
        order.extend(ai_agents)
        
        # Customer speaks about their needs
        customers = [p.participant_id for p in call_session.participants.values() 
                    if p.role == ParticipantRole.CUSTOMER]
        order.extend(customers)
        
        # Specialists provide expertise
        specialists = [p.participant_id for p in call_session.participants.values() 
                      if p.role in [ParticipantRole.SPECIALIST, ParticipantRole.SUPERVISOR]]
        order.extend(specialists)
        
        return order
    
    def _calculate_time_allocation(self, call_session: MultiParticipantCall) -> Dict[str, int]:
        """Calculate time allocation for each participant"""
        
        total_duration = call_session.expected_duration
        participant_count = len(call_session.participants)
        
        # Base time allocation
        base_time = total_duration // participant_count
        
        # Role-based adjustments
        allocations = {}
        for participant in call_session.participants.values():
            if participant.role == ParticipantRole.CUSTOMER:
                allocations[participant.participant_id] = int(base_time * 1.2)  # 20% more time
            elif participant.role == ParticipantRole.SPECIALIST:
                allocations[participant.participant_id] = int(base_time * 1.3)  # 30% more time
            elif participant.role == ParticipantRole.AI_AGENT:
                allocations[participant.participant_id] = int(base_time * 0.8)  # 20% less time
            else:
                allocations[participant.participant_id] = base_time
        
        return allocations
    
    async def _broadcast_to_participants(self, call_session: MultiParticipantCall,
                                       message: Dict[str, Any]):
        """Broadcast message to all call participants"""
        
        # In production, send via LiveKit data channel to each participant
        for participant in call_session.participants.values():
            if participant.status == ParticipantStatus.CONNECTED:
                logger.debug(f"Broadcasting to {participant.display_name}: {message['type']}")
    
    async def handle_speaking_activity(self, call_id: str, participant_id: str,
                                     speaking: bool):
        """Handle participant speaking activity"""
        
        if call_id not in self.active_calls:
            return
        
        call_session = self.active_calls[call_id]
        
        if participant_id in call_session.participants:
            participant = call_session.participants[participant_id]
            
            if speaking:
                participant.status = ParticipantStatus.SPEAKING
                call_session.current_speaker = participant_id
                participant.last_activity = datetime.now()
            else:
                participant.status = ParticipantStatus.CONNECTED
                if call_session.current_speaker == participant_id:
                    call_session.current_speaker = None
            
            # Update speaking time tracking
            await self._update_speaking_metrics(call_session, participant_id, speaking)
    
    async def _update_speaking_metrics(self, call_session: MultiParticipantCall,
                                     participant_id: str, speaking: bool):
        """Update speaking time metrics for participant"""
        
        # In production, implement actual speaking time tracking
        # This would measure actual audio activity duration
        pass
    
    async def add_specialist_to_active_call(self, call_id: str,
                                          specialist_type: HumanAgentType,
                                          reason: str) -> bool:
        """Add additional specialist to ongoing call"""
        
        if call_id not in self.active_calls:
            return False
        
        call_session = self.active_calls[call_id]
        
        # Find available specialist
        specialist = await self._find_available_specialist(specialist_type)
        if not specialist:
            logger.warning(f"No available {specialist_type.value} for call {call_id}")
            return False
        
        # Add specialist to call
        await self._add_participant_to_call(
            call_session,
            specialist.agent_id,
            specialist.name,
            ParticipantRole.SPECIALIST,
            specialist.agent_type,
            specialist.specialties
        )
        
        # Invite specialist
        await self._invite_specialist_to_call(call_session, specialist)
        
        # Notify existing participants
        notification = {
            "type": "specialist_added",
            "call_id": call_id,
            "specialist_name": specialist.name,
            "specialist_type": specialist_type.value,
            "reason": reason,
            "specialties": specialist.specialties
        }
        
        await self._broadcast_to_participants(call_session, notification)
        
        logger.info(f"Added {specialist.name} to active call {call_id}")
        return True
    
    async def transfer_call_to_specialist(self, call_id: str, specialist_id: str,
                                        transfer_reason: str) -> bool:
        """Transfer call leadership to specific specialist"""
        
        if call_id not in self.active_calls:
            return False
        
        call_session = self.active_calls[call_id]
        
        if specialist_id not in call_session.participants:
            return False
        
        specialist = call_session.participants[specialist_id]
        
        # Update specialist role to primary
        specialist.role = ParticipantRole.SUPERVISOR
        specialist.permissions.update({
            "can_end_call": True,
            "can_invite_others": True,
            "can_access_controls": True
        })
        
        # Notify all participants of transfer
        transfer_notification = {
            "type": "call_transfer",
            "call_id": call_id,
            "new_leader": specialist.display_name,
            "transfer_reason": transfer_reason,
            "message": f"Call leadership transferred to {specialist.display_name}"
        }
        
        await self._broadcast_to_participants(call_session, transfer_notification)
        
        logger.info(f"Transferred call {call_id} leadership to {specialist.display_name}")
        return True
    
    async def _start_call_recording(self, call_session: MultiParticipantCall):
        """Start recording the multi-participant call"""
        
        try:
            # In production, use LiveKit's recording capabilities
            recording_config = {
                "room_name": call_session.room_id,
                "output_format": "mp4",
                "audio_only": False,
                "layout": "grid"  # Grid layout for multi-participant
            }
            
            # Start recording via LiveKit API
            logger.info(f"Started recording for call {call_session.call_id}")
            
        except Exception as e:
            logger.error(f"Failed to start call recording: {e}")
    
    async def end_call(self, call_id: str, ended_by: str, reason: str = "completed") -> Dict[str, Any]:
        """End multi-participant call and generate summary"""
        
        if call_id not in self.active_calls:
            return {"error": "Call not found"}
        
        call_session = self.active_calls[call_id]
        call_session.call_status = "completed"
        
        # Calculate call statistics
        call_duration = (datetime.now() - call_session.started_at).total_seconds() / 60  # minutes
        
        # Generate call summary
        call_summary = await self._generate_call_summary(call_session)
        
        # Update specialist availability
        for participant in call_session.participants.values():
            if (participant.role == ParticipantRole.SPECIALIST and 
                participant.agent_type and 
                participant.participant_id in self.available_specialists):
                
                specialist = self.available_specialists[participant.participant_id]
                specialist.current_load = max(0, specialist.current_load - 1)
        
        # Store call record
        call_record = {
            "call_id": call_id,
            "call_type": call_session.call_type.value,
            "duration_minutes": call_duration,
            "participants": [
                {
                    "name": p.display_name,
                    "role": p.role.value,
                    "join_time": p.join_time.isoformat() if p.join_time else None,
                    "speaking_time": p.speaking_time
                }
                for p in call_session.participants.values()
            ],
            "action_items": call_session.action_items,
            "summary": call_summary,
            "ended_by": ended_by,
            "end_reason": reason,
            "ended_at": datetime.now().isoformat()
        }
        
        # Remove from active calls
        del self.active_calls[call_id]
        
        logger.info(f"Call {call_id} ended by {ended_by} after {call_duration:.1f} minutes")
        
        return call_record
    
    async def _generate_call_summary(self, call_session: MultiParticipantCall) -> str:
        """Generate AI-powered call summary"""
        
        # In production, use conversation transcript and context
        summary_template = f"""
        CALL SUMMARY - {call_session.call_type.value.upper()}
        
        Purpose: {call_session.call_purpose}
        Duration: {(datetime.now() - call_session.started_at).total_seconds() / 60:.1f} minutes
        Participants: {len(call_session.participants)}
        
        KEY OUTCOMES:
        - Technical consultation completed successfully
        - Customer requirements clarified
        - Implementation plan discussed
        - Next steps identified
        
        ACTION ITEMS:
        {chr(10).join(['- ' + item.get('description', '') for item in call_session.action_items])}
        
        FOLLOW-UP REQUIRED:
        - Schedule implementation planning session
        - Prepare technical documentation
        - Coordinate with customer's technical team
        """
        
        return summary_template.strip()
    
    def get_active_calls_status(self) -> Dict[str, Any]:
        """Get status of all active calls"""
        
        active_calls_info = {}
        
        for call_id, call_session in self.active_calls.items():
            duration = (datetime.now() - call_session.started_at).total_seconds() / 60
            
            active_calls_info[call_id] = {
                "call_type": call_session.call_type.value,
                "purpose": call_session.call_purpose,
                "duration_minutes": round(duration, 1),
                "participant_count": len(call_session.participants),
                "current_speaker": call_session.current_speaker,
                "status": call_session.call_status
            }
        
        return {
            "total_active_calls": len(self.active_calls),
            "calls": active_calls_info,
            "timestamp": datetime.now().isoformat()
        }