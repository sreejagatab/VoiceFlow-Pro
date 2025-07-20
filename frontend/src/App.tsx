import { useState } from 'react'
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react'
import { Room } from 'livekit-client'
import '@livekit/components-styles'
import ConversationDashboard from './components/ConversationDashboard'
import './App.css'

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || 'ws://localhost:7880'
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [token, setToken] = useState<string>('')
  const [connected, setConnected] = useState(false)
  const [room] = useState(() => new Room())
  const [loading, setLoading] = useState(false)

  const handleConnect = async () => {
    setLoading(true)
    try {
      // Get token from backend
      const response = await fetch(`${API_URL}/api/livekit/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room: 'voiceflow-room-' + Date.now(),
          username: 'customer-' + Math.random().toString(36).substr(2, 9),
          metadata: {
            type: 'customer',
            joinedAt: new Date().toISOString()
          }
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to get token')
      }
      
      const data = await response.json()
      setToken(data.token)
      setConnected(true)
    } catch (error) {
      console.error('Failed to connect:', error)
      alert('Failed to connect. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {!connected ? (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
          <div className="max-w-md w-full mx-4">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 text-center">
              <h1 className="text-3xl font-bold text-white mb-2">
                VoiceFlow Pro
              </h1>
              <p className="text-blue-200 text-lg mb-8">
                Business Automation Voice Agent
              </p>
              
              <div className="space-y-4">
                <div className="text-sm text-blue-100 text-left space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span>Lead qualification & sales support</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span>Customer support & issue resolution</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span>Appointment scheduling & calendar management</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                    <span>Real-time conversation analysis</span>
                  </div>
                </div>
                
                <button
                  onClick={handleConnect}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <span>Start Voice Conversation</span>
                  )}
                </button>
                
                <p className="text-xs text-blue-200">
                  Powered by AssemblyAI Universal-Streaming • Sub-400ms latency
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <LiveKitRoom
          video={false}
          audio={true}
          token={token}
          serverUrl={LIVEKIT_URL}
          room={room}
          onConnected={() => console.log('Connected to LiveKit room')}
          onDisconnected={() => {
            setConnected(false)
            setToken('')
          }}
          className="h-screen"
        >
          <ConversationDashboard />
          <RoomAudioRenderer />
        </LiveKitRoom>
      )}
    </div>
  )
}

export default App