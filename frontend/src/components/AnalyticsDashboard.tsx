/**
 * Real-time Conversation Analytics Dashboard for VoiceFlow Pro
 * 
 * This component provides comprehensive real-time analytics including:
 * - Live conversation metrics and performance indicators
 * - Audio quality monitoring and optimization recommendations
 * - Sentiment analysis visualization with emotional state tracking
 * - Escalation management and human agent activity
 * - Business insights and conversion tracking
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

// Types for analytics data
interface ConversationMetrics {
  timestamp: string;
  activeConversations: number;
  averageLatency: number;
  audioQuality: number;
  sentimentScore: number;
  escalationRate: number;
  conversionRate: number;
}

interface AudioMetrics {
  signalToNoiseRatio: number;
  clarityScore: number;
  naturalness: number;
  intelligibility: number;
  noiseLevel: number;
  processingLatency: number;
}

interface SentimentData {
  timestamp: string;
  sentiment: number;
  emotionalState: string;
  escalationRisk: number;
  confidence: number;
}

interface BusinessMetrics {
  leadsGenerated: number;
  appointmentsScheduled: number;
  issuesResolved: number;
  customerSatisfaction: number;
  averageCallDuration: number;
  conversionRate: number;
}

interface EscalationData {
  type: string;
  count: number;
  averageResponseTime: number;
  resolutionRate: number;
}

interface PerformanceAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
  metric: string;
  value: number;
  threshold: number;
}

const AnalyticsDashboard: React.FC = () => {
  // State management
  const [realTimeMetrics, setRealTimeMetrics] = useState<ConversationMetrics[]>([]);
  const [audioMetrics, setAudioMetrics] = useState<AudioMetrics | null>(null);
  const [sentimentData, setSentimentData] = useState<SentimentData[]>([]);
  const [businessMetrics, setBusinessMetrics] = useState<BusinessMetrics | null>(null);
  const [escalationData, setEscalationData] = useState<EscalationData[]>([]);
  const [performanceAlerts, setPerformanceAlerts] = useState<PerformanceAlert[]>([]);
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [isLiveMode, setIsLiveMode] = useState(true);

  // WebSocket connection for real-time updates
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Connect to analytics WebSocket
  const connectWebSocket = useCallback(() => {
    try {
      const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:3001'}/analytics`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Analytics WebSocket connected');
        // Request initial data
        wsRef.current?.send(JSON.stringify({
          type: 'subscribe',
          channels: ['metrics', 'audio', 'sentiment', 'business', 'escalations', 'alerts']
        }));
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = () => {
        console.log('Analytics WebSocket disconnected');
        // Attempt to reconnect after 3 seconds
        if (isLiveMode) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 3000);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('Analytics WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [isLiveMode]);

  // Handle WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'metrics_update':
        setRealTimeMetrics(prev => {
          const updated = [...prev, data.metrics];
          // Keep only last 100 data points
          return updated.slice(-100);
        });
        break;

      case 'audio_metrics':
        setAudioMetrics(data.audio);
        break;

      case 'sentiment_update':
        setSentimentData(prev => {
          const updated = [...prev, data.sentiment];
          return updated.slice(-50);
        });
        break;

      case 'business_metrics':
        setBusinessMetrics(data.business);
        break;

      case 'escalation_update':
        setEscalationData(data.escalations);
        break;

      case 'performance_alert':
        setPerformanceAlerts(prev => {
          const updated = [data.alert, ...prev];
          return updated.slice(0, 20); // Keep only last 20 alerts
        });
        break;

      case 'historical_data':
        // Handle historical data for selected time range
        setRealTimeMetrics(data.metrics || []);
        setSentimentData(data.sentiment || []);
        break;
    }
  };

  // Initialize connection
  useEffect(() => {
    if (isLiveMode) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isLiveMode, connectWebSocket]);

  // Handle time range changes
  const handleTimeRangeChange = (range: '1h' | '6h' | '24h' | '7d') => {
    setSelectedTimeRange(range);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_historical',
        timeRange: range
      }));
    }
  };

  // Format timestamp for charts
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Get current metrics summary
  const getCurrentMetrics = () => {
    const latest = realTimeMetrics[realTimeMetrics.length - 1];
    if (!latest) return null;

    return {
      activeConversations: latest.activeConversations,
      averageLatency: latest.averageLatency,
      audioQuality: latest.audioQuality,
      sentimentScore: latest.sentimentScore,
      escalationRate: latest.escalationRate,
      conversionRate: latest.conversionRate
    };
  };

  // Color schemes for charts
  const colors = {
    primary: '#3B82F6',
    success: '#10B981',
    warning: '#F59E0B',
    danger: '#EF4444',
    purple: '#8B5CF6',
    pink: '#EC4899',
    teal: '#14B8A6',
    orange: '#F97316'
  };

  const currentMetrics = getCurrentMetrics();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-600 mt-1">Real-time conversation insights and performance metrics</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Live Mode Toggle */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Live Mode</span>
              <button
                onClick={() => setIsLiveMode(!isLiveMode)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isLiveMode ? 'bg-green-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isLiveMode ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              {isLiveMode && (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-green-600 font-medium">LIVE</span>
                </div>
              )}
            </div>

            {/* Time Range Selector */}
            <div className="flex bg-white rounded-lg border p-1">
              {(['1h', '6h', '24h', '7d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => handleTimeRangeChange(range)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    selectedTimeRange === range
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Performance Alerts */}
      <AnimatePresence>
        {performanceAlerts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-6"
          >
            <div className="bg-white rounded-lg shadow-sm border p-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Performance Alerts</h3>
              <div className="space-y-2">
                {performanceAlerts.slice(0, 3).map((alert) => (
                  <div
                    key={alert.id}
                    className={`flex items-center gap-3 p-3 rounded-lg ${
                      alert.type === 'error' ? 'bg-red-50 border border-red-200' :
                      alert.type === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
                      'bg-blue-50 border border-blue-200'
                    }`}
                  >
                    <div className={`w-3 h-3 rounded-full ${
                      alert.type === 'error' ? 'bg-red-500' :
                      alert.type === 'warning' ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`} />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                      <p className="text-xs text-gray-600">
                        {alert.metric}: {alert.value} (threshold: {alert.threshold})
                      </p>
                    </div>
                    <span className="text-xs text-gray-500">{formatTimestamp(alert.timestamp)}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Key Metrics Cards */}
      {currentMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Conversations</p>
                <p className="text-2xl font-bold text-gray-900">{currentMetrics.activeConversations}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Latency</p>
                <p className="text-2xl font-bold text-gray-900">{currentMetrics.averageLatency.toFixed(0)}ms</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Audio Quality</p>
                <p className="text-2xl font-bold text-gray-900">{(currentMetrics.audioQuality * 100).toFixed(0)}%</p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 12.536a9 9 0 010-1.072m1.414-1.414a9 9 0 010 4.242m-7.071 7.071a9 9 0 010-12.728m-1.414 1.414a9 9 0 000 10.314" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Sentiment Score</p>
                <p className="text-2xl font-bold text-gray-900">{currentMetrics.sentimentScore.toFixed(1)}</p>
              </div>
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                currentMetrics.sentimentScore > 0 ? 'bg-green-100' : 'bg-red-100'
              }`}>
                <svg className={`w-6 h-6 ${
                  currentMetrics.sentimentScore > 0 ? 'text-green-600' : 'text-red-600'
                }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Escalation Rate</p>
                <p className="text-2xl font-bold text-gray-900">{(currentMetrics.escalationRate * 100).toFixed(1)}%</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.118 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Conversion Rate</p>
                <p className="text-2xl font-bold text-gray-900">{(currentMetrics.conversionRate * 100).toFixed(1)}%</p>
              </div>
              <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Real-time Metrics Chart */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Conversation Metrics</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={realTimeMetrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={formatTimestamp}
                interval="preserveStartEnd"
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => formatTimestamp(value as string)}
                formatter={(value: number, name: string) => [
                  name.includes('Rate') || name.includes('Quality') ? 
                    `${(value * 100).toFixed(1)}%` : 
                    value.toFixed(1),
                  name
                ]}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="activeConversations" 
                stroke={colors.primary} 
                strokeWidth={2}
                name="Active Conversations"
              />
              <Line 
                type="monotone" 
                dataKey="averageLatency" 
                stroke={colors.warning} 
                strokeWidth={2}
                name="Avg Latency (ms)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment Analysis Chart */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Analysis</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={sentimentData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={formatTimestamp}
                interval="preserveStartEnd"
              />
              <YAxis domain={[-1, 1]} />
              <Tooltip 
                labelFormatter={(value) => formatTimestamp(value as string)}
                formatter={(value: number, name: string) => [value.toFixed(2), name]}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="sentiment"
                stroke={colors.success}
                fill={colors.success}
                fillOpacity={0.3}
                name="Sentiment Score"
              />
              <Line
                type="monotone"
                dataKey="escalationRisk"
                stroke={colors.danger}
                strokeWidth={2}
                name="Escalation Risk"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Audio Quality and Business Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Audio Quality Radar Chart */}
        {audioMetrics && (
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Audio Quality Metrics</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={[
                { metric: 'Clarity', value: audioMetrics.clarityScore * 100 },
                { metric: 'Naturalness', value: audioMetrics.naturalness * 100 },
                { metric: 'Intelligibility', value: audioMetrics.intelligibility * 100 },
                { metric: 'SNR', value: Math.min(audioMetrics.signalToNoiseRatio * 2, 100) },
                { metric: 'Low Noise', value: (1 - audioMetrics.noiseLevel) * 100 },
                { metric: 'Low Latency', value: Math.max(0, 100 - audioMetrics.processingLatency / 5) }
              ]}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar
                  dataKey="value"
                  stroke={colors.purple}
                  fill={colors.purple}
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Business Metrics */}
        {businessMetrics && (
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Business Performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{businessMetrics.leadsGenerated}</p>
                <p className="text-sm text-gray-600">Leads Generated</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{businessMetrics.appointmentsScheduled}</p>
                <p className="text-sm text-gray-600">Appointments</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">{businessMetrics.issuesResolved}</p>
                <p className="text-sm text-gray-600">Issues Resolved</p>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <p className="text-2xl font-bold text-orange-600">{businessMetrics.customerSatisfaction.toFixed(1)}</p>
                <p className="text-sm text-gray-600">Satisfaction</p>
              </div>
            </div>
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Avg Call Duration</span>
                <span className="font-medium">{(businessMetrics.averageCallDuration / 60).toFixed(1)} min</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-sm text-gray-600">Conversion Rate</span>
                <span className="font-medium">{(businessMetrics.conversionRate * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Escalation Analytics */}
      {escalationData.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Escalation Analytics</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={escalationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill={colors.orange} name="Escalation Count" />
              </BarChart>
            </ResponsiveContainer>
            
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={escalationData}
                  dataKey="count"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) => `${entry.type}: ${entry.count}`}
                >
                  {escalationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={Object.values(colors)[index % Object.values(colors).length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;