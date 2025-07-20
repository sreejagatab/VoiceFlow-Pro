/**
 * VoiceFlow Pro React Native SDK
 * 
 * This component provides a complete React Native implementation of the VoiceFlow Pro
 * voice agent interface using LiveKit's React Native SDK.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
  PermissionsAndroid,
  AppState,
  Vibration,
} from 'react-native';
import {
  LiveKitRoom,
  useRoom,
  useParticipants,
  useTracks,
  AudioSession,
  Track,
} from '@livekit/react-native';
import { Room, RoomEvent, RemoteTrack, TrackPublication } from 'livekit-client';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';

// Import custom components
import VoiceWaveform from './components/VoiceWaveform';
import ConversationHistory from './components/ConversationHistory';
import QuickActions from './components/QuickActions';
import NotificationManager from './services/NotificationManager';

interface VoiceFlowConfig {
  livekitUrl: string;
  apiUrl: string;
  apiKey?: string;
  enableBackgroundMode?: boolean;
  enablePushNotifications?: boolean;
  audioQuality?: 'low' | 'medium' | 'high';
  enableAnalytics?: boolean;
}

interface ConversationMessage {
  id: string;
  speaker: 'customer' | 'agent';
  message: string;
  timestamp: Date;
  scenario: string;
  sentiment?: number;
}

interface AgentStatus {
  connected: boolean;
  scenario: string;
  processing: boolean;
  escalated: boolean;
}

interface VoiceFlowProSDKProps {
  config: VoiceFlowConfig;
  onConversationStart?: () => void;
  onConversationEnd?: () => void;
  onEscalation?: (reason: string) => void;
  onError?: (error: Error) => void;
  customerInfo?: {
    name?: string;
    email?: string;
    company?: string;
  };
}

export const VoiceFlowProSDK: React.FC<VoiceFlowProSDKProps> = ({
  config,
  onConversationStart,
  onConversationEnd,
  onEscalation,
  onError,
  customerInfo,
}) => {
  // State management
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>({
    connected: false,
    scenario: 'onboarding',
    processing: false,
    escalated: false,
  });
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [connectionToken, setConnectionToken] = useState<string | null>(null);
  
  // Refs and animations
  const roomRef = useRef<Room | null>(null);
  const pulseAnimation = useSharedValue(1);
  const connectionAnimation = useSharedValue(0);
  
  // Initialize audio session and permissions
  useEffect(() => {
    initializeSDK();
    setupNotifications();
    
    return () => {
      cleanup();
    };
  }, []);
  
  // Handle app state changes for background processing
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'background' && isConnected && config.enableBackgroundMode) {
        // Enable background processing
        enableBackgroundMode();
      } else if (nextAppState === 'active' && isConnected) {
        // Resume foreground processing
        disableBackgroundMode();
      }
    };
    
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  }, [isConnected, config.enableBackgroundMode]);
  
  const initializeSDK = async () => {
    try {
      // Request audio permissions
      await requestAudioPermissions();
      
      // Initialize audio session
      await AudioSession.startAudioSession();
      await AudioSession.configureAudio({
        android: {
          preferredOutputList: ['speaker'],
          audioTypeOptions: {
            manageAudioFocus: true,
            audioMode: 'normal',
            audioStreamType: 'voiceCall',
          },
        },
        ios: {
          categoryOptions: ['allowBluetooth', 'allowAirPlay', 'allowBluetoothA2DP'],
          category: 'playAndRecord',
          mode: 'voiceChat',
        },
      });
      
      // Load persisted conversation history
      await loadConversationHistory();
      
    } catch (error) {
      console.error('Failed to initialize SDK:', error);
      onError?.(error as Error);
    }
  };
  
  const requestAudioPermissions = async () => {
    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        PermissionsAndroid.PERMISSIONS.MODIFY_AUDIO_SETTINGS,
      ]);
      
      if (granted['android.permission.RECORD_AUDIO'] !== PermissionsAndroid.RESULTS.GRANTED) {
        throw new Error('Audio recording permission is required');
      }
    }
  };
  
  const setupNotifications = () => {
    if (!config.enablePushNotifications) return;
    
    PushNotification.configure({
      onNotification: function(notification) {
        if (notification.userInteraction) {
          // Handle notification tap
          handleNotificationTap(notification);
        }
      },
      requestPermissions: Platform.OS === 'ios',
    });
  };
  
  const handleNotificationTap = (notification: any) => {
    if (notification.data?.type === 'escalation') {
      // Handle escalation notification
      onEscalation?.(notification.data.reason);
    } else if (notification.data?.type === 'agent_joined') {
      // Handle human agent joining
      showAgentJoinedAlert(notification.data.agentName);
    }
  };
  
  const connectToVoiceAgent = async () => {
    if (isConnecting || isConnected) return;
    
    setIsConnecting(true);
    connectionAnimation.value = withRepeat(withTiming(1, { duration: 1000 }), -1, true);
    
    try {
      // Get connection token from backend
      const token = await getConnectionToken();
      setConnectionToken(token);
      
      onConversationStart?.();
      
    } catch (error) {
      console.error('Failed to connect:', error);
      setIsConnecting(false);
      connectionAnimation.value = 0;
      onError?.(error as Error);
      
      Alert.alert(
        'Connection Failed',
        'Unable to connect to VoiceFlow Pro. Please check your internet connection and try again.',
        [{ text: 'OK' }]
      );
    }
  };
  
  const getConnectionToken = async (): Promise<string> => {
    const response = await fetch(`${config.apiUrl}/livekit/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        room: `mobile-${Date.now()}`,
        username: customerInfo?.name || `mobile-user-${Date.now()}`,
        metadata: {
          platform: Platform.OS,
          version: Platform.Version,
          customerInfo,
          source: 'mobile_sdk',
        },
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to get connection token');
    }
    
    const data = await response.json();
    return data.token;
  };
  
  const handleRoomConnected = useCallback((room: Room) => {
    console.log('Connected to LiveKit room:', room.name);
    roomRef.current = room;
    setIsConnected(true);
    setIsConnecting(false);
    connectionAnimation.value = withTiming(0);
    
    setAgentStatus(prev => ({ ...prev, connected: true }));
    
    // Set up room event listeners
    setupRoomEventListeners(room);
    
    // Start conversation with greeting
    setTimeout(() => {
      setAgentResponse('Hello! I\'m VoiceFlow Pro, your business automation assistant. How can I help you today?');
      startPulseAnimation();
    }, 1000);
  }, []);
  
  const setupRoomEventListeners = (room: Room) => {
    room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(payload));
        handleDataMessage(data);
      } catch (error) {
        console.error('Failed to parse data message:', error);
      }
    });
    
    room.on(RoomEvent.ParticipantConnected, (participant) => {
      if (participant.identity.startsWith('human_agent_')) {
        handleHumanAgentJoined(participant);
      }
    });
    
    room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: TrackPublication) => {
      if (track.kind === Track.Kind.Audio) {
        // Handle incoming audio from agent
        handleAgentAudio(track);
      }
    });
    
    room.on(RoomEvent.Disconnected, handleRoomDisconnected);
  };
  
  const handleDataMessage = (data: any) => {
    switch (data.type) {
      case 'agent_response':
        setAgentResponse(data.message);
        addMessageToHistory('agent', data.message, data.scenario, data.sentiment);
        break;
        
      case 'transcript_update':
        setCurrentTranscript(data.transcript);
        if (data.final) {
          addMessageToHistory('customer', data.transcript, data.scenario);
          setCurrentTranscript('');
        }
        break;
        
      case 'scenario_change':
        setAgentStatus(prev => ({ ...prev, scenario: data.scenario }));
        break;
        
      case 'escalation_initiated':
        setAgentStatus(prev => ({ ...prev, escalated: true }));
        onEscalation?.(data.reason);
        showEscalationNotification(data.reason);
        break;
        
      case 'processing_status':
        setAgentStatus(prev => ({ ...prev, processing: data.processing }));
        break;
    }
  };
  
  const handleHumanAgentJoined = (participant: any) => {
    const agentName = participant.metadata?.name || 'Human Agent';
    showAgentJoinedAlert(agentName);
    
    if (config.enablePushNotifications) {
      PushNotification.localNotification({
        title: 'Human Agent Joined',
        message: `${agentName} has joined your conversation`,
        playSound: true,
        vibrate: true,
      });
    }
    
    Vibration.vibrate([0, 500, 200, 500]);
  };
  
  const handleAgentAudio = (track: RemoteTrack) => {
    // Process incoming agent audio
    startPulseAnimation();
    
    // Stop pulse when audio ends (simplified)
    setTimeout(() => {
      stopPulseAnimation();
    }, 3000);
  };
  
  const handleRoomDisconnected = useCallback(() => {
    console.log('Disconnected from LiveKit room');
    setIsConnected(false);
    setAgentStatus({
      connected: false,
      scenario: 'onboarding',
      processing: false,
      escalated: false,
    });
    
    roomRef.current = null;
    onConversationEnd?.();
  }, [onConversationEnd]);
  
  const disconnectFromVoiceAgent = async () => {
    if (roomRef.current) {
      await roomRef.current.disconnect();
    }
    
    setIsConnected(false);
    setConnectionToken(null);
    stopPulseAnimation();
    
    // Save conversation history
    await saveConversationHistory();
  };
  
  const toggleMute = async () => {
    if (roomRef.current && roomRef.current.localParticipant) {
      const enabled = !isMuted;
      await roomRef.current.localParticipant.setMicrophoneEnabled(enabled);
      setIsMuted(!enabled);
    }
  };
  
  const addMessageToHistory = (
    speaker: 'customer' | 'agent',
    message: string,
    scenario: string,
    sentiment?: number
  ) => {
    const newMessage: ConversationMessage = {
      id: `${Date.now()}-${Math.random()}`,
      speaker,
      message,
      timestamp: new Date(),
      scenario,
      sentiment,
    };
    
    setConversationHistory(prev => [...prev, newMessage]);
  };
  
  const startPulseAnimation = () => {
    pulseAnimation.value = withRepeat(
      withSpring(1.2, { damping: 2, stiffness: 100 }),
      -1,
      true
    );
  };
  
  const stopPulseAnimation = () => {
    pulseAnimation.value = withSpring(1);
  };
  
  const showAgentJoinedAlert = (agentName: string) => {
    Alert.alert(
      'Human Agent Joined',
      `${agentName} has joined your conversation to provide specialized assistance.`,
      [{ text: 'OK' }]
    );
  };
  
  const showEscalationNotification = (reason: string) => {
    if (config.enablePushNotifications) {
      PushNotification.localNotification({
        title: 'Conversation Escalated',
        message: `Your conversation has been escalated: ${reason}`,
        playSound: true,
        vibrate: true,
      });
    }
  };
  
  const enableBackgroundMode = async () => {
    // Enable background audio processing
    if (Platform.OS === 'ios') {
      await AudioSession.configureAudio({
        ios: {
          category: 'playAndRecord',
          mode: 'voiceChat',
          categoryOptions: ['allowBluetooth', 'mixWithOthers'],
        },
      });
    }
  };
  
  const disableBackgroundMode = async () => {
    // Resume normal audio processing
    if (Platform.OS === 'ios') {
      await AudioSession.configureAudio({
        ios: {
          category: 'playAndRecord',
          mode: 'voiceChat',
          categoryOptions: ['allowBluetooth'],
        },
      });
    }
  };
  
  const loadConversationHistory = async () => {
    try {
      const stored = await AsyncStorage.getItem('voiceflow_conversation_history');
      if (stored) {
        const history = JSON.parse(stored);
        setConversationHistory(history.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })));
      }
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    }
  };
  
  const saveConversationHistory = async () => {
    try {
      await AsyncStorage.setItem(
        'voiceflow_conversation_history',
        JSON.stringify(conversationHistory)
      );
    } catch (error) {
      console.error('Failed to save conversation history:', error);
    }
  };
  
  const cleanup = async () => {
    await saveConversationHistory();
    await AudioSession.stopAudioSession();
    if (roomRef.current) {
      await roomRef.current.disconnect();
    }
  };
  
  // Animated styles
  const pulseStyle = useAnimatedStyle(() => {
    return {
      transform: [{ scale: pulseAnimation.value }],
    };
  });
  
  const connectionStyle = useAnimatedStyle(() => {
    return {
      opacity: 0.5 + 0.5 * connectionAnimation.value,
    };
  });
  
  const getScenarioColor = (scenario: string): string => {
    const colors = {
      onboarding: '#3B82F6',
      sales: '#10B981',
      support: '#EF4444',
      scheduling: '#8B5CF6',
      escalation: '#F59E0B',
    };
    return colors[scenario as keyof typeof colors] || '#6B7280';
  };
  
  const getScenarioIcon = (scenario: string): string => {
    const icons = {
      onboarding: 'waving-hand',
      sales: 'trending-up',
      support: 'support-agent',
      scheduling: 'event',
      escalation: 'priority-high',
    };
    return icons[scenario as keyof typeof icons] || 'chat';
  };
  
  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <Text style={styles.title}>VoiceFlow Pro</Text>
          <View style={[styles.scenarioTag, { backgroundColor: getScenarioColor(agentStatus.scenario) }]}>
            <Icon name={getScenarioIcon(agentStatus.scenario)} size={16} color="white" />
            <Text style={styles.scenarioText}>{agentStatus.scenario}</Text>
          </View>
        </View>
        
        <View style={styles.statusIndicator}>
          {isConnecting ? (
            <Animated.View style={[styles.statusDot, styles.connecting, connectionStyle]} />
          ) : (
            <View style={[styles.statusDot, isConnected ? styles.connected : styles.disconnected]} />
          )}
        </View>
      </View>
      
      {/* Main Content */}
      {!isConnected ? (
        <View style={styles.connectScreen}>
          <View style={styles.welcomeContent}>
            <Text style={styles.welcomeTitle}>Welcome to VoiceFlow Pro</Text>
            <Text style={styles.welcomeSubtitle}>
              Your intelligent business automation voice assistant
            </Text>
            
            <View style={styles.featureList}>
              <Text style={styles.featureItem}>• Lead qualification & sales support</Text>
              <Text style={styles.featureItem}>• Customer support & issue resolution</Text>
              <Text style={styles.featureItem}>• Appointment scheduling</Text>
              <Text style={styles.featureItem}>• Real-time conversation analysis</Text>
            </View>
            
            <TouchableOpacity
              style={[styles.connectButton, isConnecting && styles.connectingButton]}
              onPress={connectToVoiceAgent}
              disabled={isConnecting}
            >
              {isConnecting ? (
                <Animated.View style={connectionStyle}>
                  <Text style={styles.connectButtonText}>Connecting...</Text>
                </Animated.View>
              ) : (
                <Text style={styles.connectButtonText}>Start Conversation</Text>
              )}
            </TouchableOpacity>
            
            <Text style={styles.poweredBy}>
              Powered by AssemblyAI Universal-Streaming • Sub-400ms latency
            </Text>
          </View>
        </View>
      ) : (
        <>
          {connectionToken && (
            <LiveKitRoom
              serverUrl={config.livekitUrl}
              token={connectionToken}
              connect={true}
              onConnected={handleRoomConnected}
              onDisconnected={handleRoomDisconnected}
              audio={true}
              video={false}
              options={{
                adaptiveStream: true,
                dynacast: true,
                publishDefaults: {
                  audioPreset: {
                    maxBitrate: 64000,
                    priority: 'high',
                  },
                },
              }}
            >
              <ConversationInterface
                agentStatus={agentStatus}
                conversationHistory={conversationHistory}
                currentTranscript={currentTranscript}
                agentResponse={agentResponse}
                isMuted={isMuted}
                onToggleMute={toggleMute}
                onDisconnect={disconnectFromVoiceAgent}
                pulseStyle={pulseStyle}
              />
            </LiveKitRoom>
          )}
        </>
      )}
    </View>
  );
};

// Conversation Interface Component
const ConversationInterface: React.FC<{
  agentStatus: AgentStatus;
  conversationHistory: ConversationMessage[];
  currentTranscript: string;
  agentResponse: string;
  isMuted: boolean;
  onToggleMute: () => void;
  onDisconnect: () => void;
  pulseStyle: any;
}> = ({
  agentStatus,
  conversationHistory,
  currentTranscript,
  agentResponse,
  isMuted,
  onToggleMute,
  onDisconnect,
  pulseStyle,
}) => {
  return (
    <View style={styles.conversationContainer}>
      {/* Live Conversation Area */}
      <View style={styles.liveArea}>
        {/* Agent Response */}
        <View style={styles.agentResponseContainer}>
          <View style={styles.responseHeader}>
            <Icon name="volume-up" size={20} color="#8B5CF6" />
            <Text style={styles.responseLabel}>VoiceFlow Pro</Text>
            {agentStatus.processing && (
              <View style={styles.processingIndicator}>
                <Text style={styles.processingText}>Processing...</Text>
              </View>
            )}
          </View>
          <Text style={styles.agentResponseText}>
            {agentResponse || 'Listening...'}
          </Text>
        </View>
        
        {/* Customer Input */}
        {currentTranscript && (
          <View style={styles.customerInputContainer}>
            <View style={styles.inputHeader}>
              <Icon name="mic" size={20} color="#10B981" />
              <Text style={styles.inputLabel}>You're speaking</Text>
            </View>
            <Text style={styles.customerInputText}>{currentTranscript}</Text>
          </View>
        )}
        
        {/* Voice Waveform */}
        <VoiceWaveform isActive={!isMuted && agentStatus.connected} />
      </View>
      
      {/* Conversation History */}
      <ConversationHistory messages={conversationHistory} />
      
      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.controlButton, isMuted && styles.mutedButton]}
          onPress={onToggleMute}
        >
          <Animated.View style={pulseStyle}>
            <Icon 
              name={isMuted ? 'mic-off' : 'mic'} 
              size={24} 
              color={isMuted ? '#EF4444' : '#FFFFFF'} 
            />
          </Animated.View>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.endCallButton} onPress={onDisconnect}>
          <Icon name="call-end" size={24} color="#FFFFFF" />
        </TouchableOpacity>
      </View>
      
      {/* Quick Actions */}
      <QuickActions scenario={agentStatus.scenario} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'ios' ? 50 : 20,
    paddingBottom: 15,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1F2937',
    marginRight: 12,
  },
  scenarioTag: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  scenarioText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 4,
    textTransform: 'capitalize',
  },
  statusIndicator: {
    alignItems: 'center',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  connected: {
    backgroundColor: '#10B981',
  },
  disconnected: {
    backgroundColor: '#EF4444',
  },
  connecting: {
    backgroundColor: '#F59E0B',
  },
  connectScreen: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  welcomeContent: {
    alignItems: 'center',
    maxWidth: 320,
  },
  welcomeTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1F2937',
    textAlign: 'center',
    marginBottom: 8,
  },
  welcomeSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 32,
  },
  featureList: {
    alignSelf: 'stretch',
    marginBottom: 32,
  },
  featureItem: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 8,
  },
  connectButton: {
    backgroundColor: '#3B82F6',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
    marginBottom: 16,
    minWidth: 200,
  },
  connectingButton: {
    backgroundColor: '#93C5FD',
  },
  connectButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  poweredBy: {
    fontSize: 12,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  conversationContainer: {
    flex: 1,
  },
  liveArea: {
    backgroundColor: '#FFFFFF',
    margin: 16,
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  agentResponseContainer: {
    marginBottom: 16,
  },
  responseHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  responseLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#8B5CF6',
    marginLeft: 8,
  },
  processingIndicator: {
    marginLeft: 'auto',
  },
  processingText: {
    fontSize: 12,
    color: '#F59E0B',
    fontWeight: '500',
  },
  agentResponseText: {
    fontSize: 16,
    color: '#1F2937',
    lineHeight: 24,
  },
  customerInputContainer: {
    backgroundColor: '#F3F4F6',
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
  },
  inputHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: '#10B981',
    marginLeft: 8,
  },
  customerInputText: {
    fontSize: 16,
    color: '#1F2937',
    lineHeight: 24,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  controlButton: {
    backgroundColor: '#3B82F6',
    width: 64,
    height: 64,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 20,
  },
  mutedButton: {
    backgroundColor: '#EF4444',
  },
  endCallButton: {
    backgroundColor: '#EF4444',
    width: 64,
    height: 64,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default VoiceFlowProSDK;