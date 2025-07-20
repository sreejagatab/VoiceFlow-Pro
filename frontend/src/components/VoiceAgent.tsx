import { useState, useEffect } from 'react'
import { useConnectionState, useRoomContext, useTracks } from '@livekit/components-react'
import { ConnectionState, Track } from 'livekit-client'
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react'

export default function VoiceAgent() {
  const room = useRoomContext()
  const connectionState = useConnectionState()
  const tracks = useTracks([Track.Source.Microphone])
  
  const [isMuted, setIsMuted] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [agentResponse, setAgentResponse] = useState('')

  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      console.log('Connected to LiveKit room')
      setAgentResponse('Hello! I\'m VoiceFlow Pro. How can I help you with your business needs today?')
    }
  }, [connectionState])

  const toggleMute = () => {
    if (room) {
      room.localParticipant.setMicrophoneEnabled(isMuted)
      setIsMuted(!isMuted)
    }
  }

  const getConnectionStatus = () => {
    switch (connectionState) {
      case ConnectionState.Connected:
        return { text: 'Connected', color: 'text-green-400' }
      case ConnectionState.Connecting:
        return { text: 'Connecting...', color: 'text-yellow-400' }
      case ConnectionState.Disconnected:
        return { text: 'Disconnected', color: 'text-red-400' }
      default:
        return { text: 'Unknown', color: 'text-gray-400' }
    }
  }

  const status = getConnectionStatus()

  return (
    <div className="voice-agent-container p-6 text-white">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${connectionState === ConnectionState.Connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className={status.color}>{status.text}</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={toggleMute}
            className={`p-2 rounded-full transition-colors ${
              isMuted 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="bg-black/20 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Volume2 size={16} className="text-blue-400" />
            <span className="text-sm font-medium text-blue-400">Agent Response</span>
          </div>
          <p className="text-white">
            {agentResponse || 'Waiting for agent response...'}
          </p>
        </div>

        {isListening && (
          <div className="bg-black/20 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Mic size={16} className="text-green-400" />
              <span className="text-sm font-medium text-green-400">You're speaking</span>
            </div>
            <p className="text-white">
              {transcript || 'Listening...'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-300">
          Powered by LiveKit + AssemblyAI Universal-Streaming
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Sub-400ms latency for natural conversation
        </p>
      </div>
    </div>
  )
}