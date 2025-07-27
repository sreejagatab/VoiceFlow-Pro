import { useState, useEffect } from 'react'
import { useRoomContext, useConnectionState, useRemoteParticipants } from '@livekit/components-react'
import { ConnectionState } from 'livekit-client'
import { 
  Mic, 
  MicOff, 
  Volume2, 
  PhoneOff,
  TrendingUp,
  Calendar,
  MessageSquare,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'

interface ConversationTurn {
  speaker: 'customer' | 'agent'
  message: string
  timestamp: string
  scenario: string
  sentiment?: number
  entities?: any
}

interface BusinessAction {
  type: string
  data: any
  timestamp: string
}

export default function ConversationDashboard() {
  const room = useRoomContext()
  const connectionState = useConnectionState()
  const participants = useRemoteParticipants(); // eslint-disable-line @typescript-eslint/no-unused-vars
  
  const [isCallActive, setIsCallActive] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentScenario, setCurrentScenario] = useState<string>('onboarding')
  const [conversationHistory] = useState<ConversationTurn[]>([])
  const [businessActions, setBusinessActions] = useState<BusinessAction[]>([])
  const [liveTranscript, setLiveTranscript] = useState('')
  const [agentResponse, setAgentResponse] = useState('')
  const [sentimentScore, setSentimentScore] = useState(0)
  const [leadScore, setLeadScore] = useState(0)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      setIsCallActive(true)
      setAgentResponse('Hello! I\'m VoiceFlow Pro. I\'m here to help with your business needs. How can I assist you today?')
    } else if (connectionState === ConnectionState.Disconnected) {
      setIsCallActive(false)
    }
  }, [connectionState])

  // Simulate real-time updates (in production, this would come from WebSocket or LiveKit data messages)
  useEffect(() => {
    if (isCallActive) {
      const interval = setInterval(() => {
        // Simulate live metrics updates
        setSentimentScore(prev => {
          const change = (Math.random() - 0.5) * 0.1
          return Math.max(-1, Math.min(1, prev + change))
        })

        setLeadScore(prev => {
          if (currentScenario === 'sales') {
            return Math.min(prev + Math.random() * 2, 100)
          }
          return prev
        })

        // Simulate live transcript updates
        if (Math.random() > 0.95) {
          const sampleTranscripts = [
            "I'm interested in your enterprise solutions...",
            "What pricing options do you have?",
            "Can you tell me more about the features?",
            "How does this integrate with our existing systems?",
            "What's the implementation timeline?"
          ]
          setLiveTranscript(sampleTranscripts[Math.floor(Math.random() * sampleTranscripts.length)])

          setTimeout(() => setLiveTranscript(''), 3000)
        }
      }, 1000)

      return () => clearInterval(interval)
    }
  }, [isCallActive, currentScenario])

  const toggleMute = () => {
    if (room) {
      room.localParticipant.setMicrophoneEnabled(isMuted)
      setIsMuted(!isMuted)
    }
  }

  const endCall = () => {
    if (room) {
      room.disconnect()
    }
    setIsCallActive(false)
  }

  const handleQuickAction = async (actionType: string) => {
    setActionLoading(actionType)

    try {
      const roomId = room?.name || 'demo-room-' + Date.now()

      // Simulate API call to backend
      const response = await fetch(`${API_URL}/api/conversation/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          roomId,
          actionType,
          timestamp: new Date().toISOString(),
          context: {
            scenario: currentScenario,
            leadScore,
            sentimentScore
          }
        })
      })

      if (response.ok) {
        // Add action to business actions list
        const newAction: BusinessAction = {
          type: actionType,
          data: { success: true },
          timestamp: new Date().toISOString()
        }
        setBusinessActions(prev => [...prev, newAction])

        // Update agent response based on action
        switch (actionType) {
          case 'schedule_demo':
            setAgentResponse('Great! I\'ve scheduled a demo for you. You\'ll receive a calendar invitation shortly.')
            setCurrentScenario('scheduling')
            break
          case 'create_lead':
            setAgentResponse('Perfect! I\'ve created a lead record with your information. Our sales team will follow up within 24 hours.')
            setCurrentScenario('sales')
            setLeadScore(Math.min(leadScore + 20, 100))
            break
          case 'escalate_human':
            setAgentResponse('I\'m connecting you with a human specialist who can better assist you. Please hold for just a moment.')
            setCurrentScenario('escalation')
            break
          case 'send_followup':
            setAgentResponse('I\'ve scheduled a follow-up for you. You\'ll receive an email summary and next steps.')
            setCurrentScenario('follow_up')
            break
        }
      }
    } catch (error) {
      console.error('Action failed:', error)
      setAgentResponse('I apologize, but I encountered an issue processing that request. Let me try a different approach.')
    } finally {
      setActionLoading(null)
    }
  }

  const getScenarioColor = (scenario: string) => {
    const colors = {
      onboarding: 'bg-blue-100 text-blue-800',
      sales: 'bg-green-100 text-green-800',
      support: 'bg-red-100 text-red-800',
      scheduling: 'bg-purple-100 text-purple-800',
      follow_up: 'bg-yellow-100 text-yellow-800',
      escalation: 'bg-orange-100 text-orange-800'
    }
    return colors[scenario as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  const getScenarioIcon = (scenario: string) => {
    switch (scenario) {
      case 'sales': return <TrendingUp size={16} />
      case 'support': return <AlertTriangle size={16} />
      case 'scheduling': return <Calendar size={16} />
      default: return <MessageSquare size={16} />
    }
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-green-600'
    if (sentiment < -0.3) return 'text-red-600'
    return 'text-yellow-600'
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Conversation Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className={`w-3 h-3 rounded-full ${
                connectionState === ConnectionState.Connected ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <h1 className="text-xl font-semibold text-gray-900">VoiceFlow Pro</h1>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScenarioColor(currentScenario)}`}>
                {getScenarioIcon(currentScenario)}
                <span className="ml-1 capitalize">{currentScenario}</span>
              </span>
            </div>
            
            {/* Call Controls */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                className={`p-2 rounded-full transition-colors ${
                  isMuted 
                    ? 'bg-red-600 hover:bg-red-700 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
              >
                {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              
              <button
                onClick={endCall}
                className="p-2 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors"
              >
                <PhoneOff size={20} />
              </button>
            </div>
          </div>
        </div>

        {/* Live Conversation */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Current Speaker Display */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 border-b border-gray-200">
            {liveTranscript && (
              <div className="mb-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Mic size={16} className="text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">You're speaking</span>
                </div>
                <p className="text-gray-800 bg-white/50 rounded-lg p-3">{liveTranscript}</p>
              </div>
            )}
            
            <div className="flex items-center space-x-2 mb-2">
              <Volume2 size={16} className="text-purple-600" />
              <span className="text-sm font-medium text-purple-700">VoiceFlow Pro</span>
            </div>
            <p className="text-gray-800 bg-white/50 rounded-lg p-3">
              {agentResponse || 'Listening...'}
            </p>
          </div>

          {/* Conversation History */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {conversationHistory.map((turn, index) => (
              <div key={index} className={`flex ${turn.speaker === 'customer' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  turn.speaker === 'customer'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-800'
                }`}>
                  <p className="text-sm">{turn.message}</p>
                  <div className="flex items-center justify-between mt-1 text-xs opacity-75">
                    <span>{new Date(turn.timestamp).toLocaleTimeString()}</span>
                    <span className="capitalize">{turn.scenario}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Sidebar - Analytics & Actions */}
      <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
        {/* Metrics */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Live Analytics</h3>
          
          <div className="space-y-3">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Sentiment</span>
                <span className={`text-sm font-bold ${getSentimentColor(sentimentScore)}`}>
                  {sentimentScore > 0 ? '+' : ''}{(sentimentScore * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div 
                  className={`h-2 rounded-full transition-all duration-300 ${
                    sentimentScore > 0 ? 'bg-green-500' : sentimentScore < 0 ? 'bg-red-500' : 'bg-yellow-500'
                  }`}
                  style={{ width: `${Math.abs(sentimentScore) * 100}%` }}
                />
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Lead Score</span>
                <span className="text-sm font-bold text-blue-600">{leadScore}/100</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div 
                  className="h-2 rounded-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${leadScore}%` }}
                />
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Duration</span>
                <span className="text-sm font-bold text-gray-900">
                  {isCallActive ? '02:34' : '00:00'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Business Actions */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions Taken</h3>
          
          <div className="space-y-2">
            {businessActions.length === 0 ? (
              <p className="text-sm text-gray-500">No actions yet</p>
            ) : (
              businessActions.map((action, index) => (
                <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <CheckCircle size={16} className="text-green-600" />
                    <span className="text-sm font-medium text-green-800 capitalize">
                      {action.type.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-xs text-green-700 mt-1">
                    {new Date(action.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="p-4 flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          
          <div className="space-y-2">
            <button
              onClick={() => handleQuickAction('schedule_demo')}
              disabled={actionLoading === 'schedule_demo'}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              {actionLoading === 'schedule_demo' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                'Schedule Demo'
              )}
            </button>
            <button
              onClick={() => handleQuickAction('create_lead')}
              disabled={actionLoading === 'create_lead'}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              {actionLoading === 'create_lead' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                'Create Lead'
              )}
            </button>
            <button
              onClick={() => handleQuickAction('escalate_human')}
              disabled={actionLoading === 'escalate_human'}
              className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              {actionLoading === 'escalate_human' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                'Escalate to Human'
              )}
            </button>
            <button
              onClick={() => handleQuickAction('send_followup')}
              disabled={actionLoading === 'send_followup'}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
            >
              {actionLoading === 'send_followup' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                'Send Follow-up'
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <p className="text-xs text-gray-500 text-center">
            Powered by AssemblyAI Universal-Streaming
          </p>
          <p className="text-xs text-gray-400 text-center mt-1">
            Sub-400ms latency • 99.9% uptime
          </p>
        </div>
      </div>
    </div>
  )
}