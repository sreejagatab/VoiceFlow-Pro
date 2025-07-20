/**
 * Real-time Analytics Service for VoiceFlow Pro
 * 
 * This service provides comprehensive analytics collection and real-time streaming including:
 * - Conversation metrics tracking and aggregation
 * - Audio quality monitoring and analysis
 * - Sentiment analysis data collection
 * - Business performance metrics calculation
 * - Escalation analytics and reporting
 * - Real-time WebSocket streaming to dashboard
 */

import { WebSocket } from 'ws';
import { EventEmitter } from 'events';
import { DatabaseClient } from '../database/client.js';
import Redis from 'ioredis';

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

export class AnalyticsService extends EventEmitter {
  private db: DatabaseClient;
  private redis: Redis;
  private connectedClients: Set<WebSocket>;
  private metricsInterval: NodeJS.Timeout | null;
  private businessMetricsInterval: NodeJS.Timeout | null;
  
  // Real-time data stores
  private realtimeMetrics: ConversationMetrics[] = [];
  private sentimentData: SentimentData[] = [];
  private performanceAlerts: PerformanceAlert[] = [];
  
  // Performance thresholds
  private thresholds = {
    latency: {
      warning: 800,  // ms
      error: 1500    // ms
    },
    audioQuality: {
      warning: 0.7,
      error: 0.5
    },
    escalationRate: {
      warning: 0.15, // 15%
      error: 0.25    // 25%
    },
    sentiment: {
      warning: -0.3,
      error: -0.6
    }
  };

  constructor() {
    super();
    this.db = new DatabaseClient();
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    this.connectedClients = new Set();
    this.metricsInterval = null;
    this.businessMetricsInterval = null;
    
    this.initializeAnalytics();
  }

  private async initializeAnalytics() {
    try {
      // Start real-time metrics collection
      this.startMetricsCollection();
      
      // Start business metrics calculation
      this.startBusinessMetricsCalculation();
      
      // Subscribe to Redis events
      this.subscribeToEvents();
      
      console.log('Analytics service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize analytics service:', error);
    }
  }

  private startMetricsCollection() {
    // Collect metrics every 10 seconds
    this.metricsInterval = setInterval(async () => {
      try {
        const metrics = await this.collectConversationMetrics();
        this.realtimeMetrics.push(metrics);
        
        // Keep only last 1000 data points (about 2.7 hours at 10s intervals)
        if (this.realtimeMetrics.length > 1000) {
          this.realtimeMetrics = this.realtimeMetrics.slice(-1000);
        }
        
        // Check for performance alerts
        await this.checkPerformanceThresholds(metrics);
        
        // Broadcast to connected clients
        this.broadcastToClients('metrics_update', { metrics });
        
      } catch (error) {
        console.error('Error collecting conversation metrics:', error);
      }
    }, 10000);
  }

  private startBusinessMetricsCalculation() {
    // Calculate business metrics every 5 minutes
    this.businessMetricsInterval = setInterval(async () => {
      try {
        const businessMetrics = await this.calculateBusinessMetrics();
        this.broadcastToClients('business_metrics', { business: businessMetrics });
      } catch (error) {
        console.error('Error calculating business metrics:', error);
      }
    }, 5 * 60 * 1000);
  }

  private subscribeToEvents() {
    // Subscribe to Redis channels for real-time events
    const subscriber = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    
    subscriber.subscribe('audio_metrics', 'sentiment_update', 'escalation_event');
    
    subscriber.on('message', (channel: string, message: string) => {
      try {
        const data = JSON.parse(message);
        
        switch (channel) {
          case 'audio_metrics':
            this.broadcastToClients('audio_metrics', { audio: data });
            break;
            
          case 'sentiment_update':
            this.handleSentimentUpdate(data);
            break;
            
          case 'escalation_event':
            this.handleEscalationEvent(data);
            break;
        }
      } catch (error) {
        console.error('Error processing Redis message:', error);
      }
    });
  }

  private async collectConversationMetrics(): Promise<ConversationMetrics> {
    const now = new Date();
    const timestamp = now.toISOString();
    
    // Get active conversations count
    const activeConversations = await this.getActiveConversationsCount();
    
    // Calculate average latency from recent conversations
    const averageLatency = await this.calculateAverageLatency();
    
    // Get average audio quality from recent sessions
    const audioQuality = await this.calculateAverageAudioQuality();
    
    // Calculate average sentiment score
    const sentimentScore = await this.calculateAverageSentiment();
    
    // Calculate escalation rate
    const escalationRate = await this.calculateEscalationRate();
    
    // Calculate conversion rate
    const conversionRate = await this.calculateConversionRate();
    
    return {
      timestamp,
      activeConversations,
      averageLatency,
      audioQuality,
      sentimentScore,
      escalationRate,
      conversionRate
    };
  }

  private async getActiveConversationsCount(): Promise<number> {
    try {
      const query = `
        SELECT COUNT(*) as count
        FROM conversations 
        WHERE status = 'active' 
          AND updated_at > NOW() - INTERVAL '5 minutes'
      `;
      
      const result = await this.db.query(query);
      return parseInt(result.rows[0]?.count || '0');
    } catch (error) {
      console.error('Error getting active conversations count:', error);
      return 0;
    }
  }

  private async calculateAverageLatency(): Promise<number> {
    try {
      const query = `
        SELECT AVG(
          EXTRACT(EPOCH FROM (response_time - request_time)) * 1000
        ) as avg_latency
        FROM conversation_turns 
        WHERE created_at > NOW() - INTERVAL '10 minutes'
          AND response_time IS NOT NULL
      `;
      
      const result = await this.db.query(query);
      return parseFloat(result.rows[0]?.avg_latency || '0');
    } catch (error) {
      console.error('Error calculating average latency:', error);
      return 0;
    }
  }

  private async calculateAverageAudioQuality(): Promise<number> {
    try {
      // Get cached audio quality metrics from Redis
      const cached = await this.redis.get('avg_audio_quality');
      if (cached) {
        return parseFloat(cached);
      }
      
      // Fallback to database query
      const query = `
        SELECT AVG(audio_quality_score) as avg_quality
        FROM conversation_sessions 
        WHERE created_at > NOW() - INTERVAL '10 minutes'
          AND audio_quality_score IS NOT NULL
      `;
      
      const result = await this.db.query(query);
      const quality = parseFloat(result.rows[0]?.avg_quality || '0.8');
      
      // Cache for 1 minute
      await this.redis.setex('avg_audio_quality', 60, quality.toString());
      
      return quality;
    } catch (error) {
      console.error('Error calculating average audio quality:', error);
      return 0.8; // Default reasonable value
    }
  }

  private async calculateAverageSentiment(): Promise<number> {
    try {
      const query = `
        SELECT AVG(sentiment_score) as avg_sentiment
        FROM conversation_turns 
        WHERE created_at > NOW() - INTERVAL '10 minutes'
          AND sentiment_score IS NOT NULL
      `;
      
      const result = await this.db.query(query);
      return parseFloat(result.rows[0]?.avg_sentiment || '0');
    } catch (error) {
      console.error('Error calculating average sentiment:', error);
      return 0;
    }
  }

  private async calculateEscalationRate(): Promise<number> {
    try {
      const query = `
        SELECT 
          COUNT(CASE WHEN escalated = true THEN 1 END)::float / 
          NULLIF(COUNT(*), 0) as escalation_rate
        FROM conversations 
        WHERE created_at > NOW() - INTERVAL '1 hour'
      `;
      
      const result = await this.db.query(query);
      return parseFloat(result.rows[0]?.escalation_rate || '0');
    } catch (error) {
      console.error('Error calculating escalation rate:', error);
      return 0;
    }
  }

  private async calculateConversionRate(): Promise<number> {
    try {
      const query = `
        SELECT 
          COUNT(CASE WHEN outcome IN ('sale', 'appointment', 'qualified_lead') THEN 1 END)::float /
          NULLIF(COUNT(*), 0) as conversion_rate
        FROM conversations 
        WHERE created_at > NOW() - INTERVAL '1 hour'
          AND status = 'completed'
      `;
      
      const result = await this.db.query(query);
      return parseFloat(result.rows[0]?.conversion_rate || '0');
    } catch (error) {
      console.error('Error calculating conversion rate:', error);
      return 0;
    }
  }

  private async calculateBusinessMetrics(): Promise<BusinessMetrics> {
    try {
      const timeframe = "NOW() - INTERVAL '24 hours'";
      
      // Leads generated
      const leadsQuery = `
        SELECT COUNT(*) as count
        FROM customers 
        WHERE created_at > ${timeframe}
          AND lead_score > 50
      `;
      const leadsResult = await this.db.query(leadsQuery);
      const leadsGenerated = parseInt(leadsResult.rows[0]?.count || '0');
      
      // Appointments scheduled
      const appointmentsQuery = `
        SELECT COUNT(*) as count
        FROM business_actions 
        WHERE action_type = 'appointment_scheduled'
          AND created_at > ${timeframe}
      `;
      const appointmentsResult = await this.db.query(appointmentsQuery);
      const appointmentsScheduled = parseInt(appointmentsResult.rows[0]?.count || '0');
      
      // Issues resolved
      const issuesQuery = `
        SELECT COUNT(*) as count
        FROM conversations 
        WHERE outcome = 'resolved'
          AND created_at > ${timeframe}
      `;
      const issuesResult = await this.db.query(issuesQuery);
      const issuesResolved = parseInt(issuesResult.rows[0]?.count || '0');
      
      // Customer satisfaction
      const satisfactionQuery = `
        SELECT AVG(satisfaction_rating) as avg_rating
        FROM conversations 
        WHERE satisfaction_rating IS NOT NULL
          AND created_at > ${timeframe}
      `;
      const satisfactionResult = await this.db.query(satisfactionQuery);
      const customerSatisfaction = parseFloat(satisfactionResult.rows[0]?.avg_rating || '4.0');
      
      // Average call duration
      const durationQuery = `
        SELECT AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) as avg_duration
        FROM conversations 
        WHERE ended_at IS NOT NULL
          AND created_at > ${timeframe}
      `;
      const durationResult = await this.db.query(durationQuery);
      const averageCallDuration = parseFloat(durationResult.rows[0]?.avg_duration || '180');
      
      // Conversion rate (24h)
      const conversionQuery = `
        SELECT 
          COUNT(CASE WHEN outcome IN ('sale', 'appointment', 'qualified_lead') THEN 1 END)::float /
          NULLIF(COUNT(*), 0) as conversion_rate
        FROM conversations 
        WHERE created_at > ${timeframe}
          AND status = 'completed'
      `;
      const conversionResult = await this.db.query(conversionQuery);
      const conversionRate = parseFloat(conversionResult.rows[0]?.conversion_rate || '0');
      
      return {
        leadsGenerated,
        appointmentsScheduled,
        issuesResolved,
        customerSatisfaction,
        averageCallDuration,
        conversionRate
      };
    } catch (error) {
      console.error('Error calculating business metrics:', error);
      return {
        leadsGenerated: 0,
        appointmentsScheduled: 0,
        issuesResolved: 0,
        customerSatisfaction: 4.0,
        averageCallDuration: 180,
        conversionRate: 0
      };
    }
  }

  private handleSentimentUpdate(data: any) {
    const sentimentData: SentimentData = {
      timestamp: new Date().toISOString(),
      sentiment: data.sentiment || 0,
      emotionalState: data.emotionalState || 'neutral',
      escalationRisk: data.escalationRisk || 0,
      confidence: data.confidence || 0
    };
    
    this.sentimentData.push(sentimentData);
    
    // Keep only last 200 sentiment data points
    if (this.sentimentData.length > 200) {
      this.sentimentData = this.sentimentData.slice(-200);
    }
    
    this.broadcastToClients('sentiment_update', { sentiment: sentimentData });
  }

  private async handleEscalationEvent(data: any) {
    try {
      // Calculate escalation analytics
      const escalationData = await this.calculateEscalationAnalytics();
      this.broadcastToClients('escalation_update', { escalations: escalationData });
    } catch (error) {
      console.error('Error handling escalation event:', error);
    }
  }

  private async calculateEscalationAnalytics(): Promise<EscalationData[]> {
    try {
      const query = `
        SELECT 
          escalation_type as type,
          COUNT(*) as count,
          AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) as avg_response_time,
          COUNT(CASE WHEN status = 'resolved' THEN 1 END)::float / COUNT(*) as resolution_rate
        FROM escalations 
        WHERE created_at > NOW() - INTERVAL '24 hours'
        GROUP BY escalation_type
        ORDER BY count DESC
      `;
      
      const result = await this.db.query(query);
      
      return result.rows.map(row => ({
        type: row.type,
        count: parseInt(row.count),
        averageResponseTime: parseFloat(row.avg_response_time || '0'),
        resolutionRate: parseFloat(row.resolution_rate || '0')
      }));
    } catch (error) {
      console.error('Error calculating escalation analytics:', error);
      return [];
    }
  }

  private async checkPerformanceThresholds(metrics: ConversationMetrics) {
    const alerts: PerformanceAlert[] = [];
    
    // Check latency thresholds
    if (metrics.averageLatency > this.thresholds.latency.error) {
      alerts.push({
        id: `latency-${Date.now()}`,
        type: 'error',
        message: 'Critical latency detected - response times are extremely high',
        timestamp: new Date().toISOString(),
        metric: 'averageLatency',
        value: metrics.averageLatency,
        threshold: this.thresholds.latency.error
      });
    } else if (metrics.averageLatency > this.thresholds.latency.warning) {
      alerts.push({
        id: `latency-${Date.now()}`,
        type: 'warning',
        message: 'High latency detected - response times are above normal',
        timestamp: new Date().toISOString(),
        metric: 'averageLatency',
        value: metrics.averageLatency,
        threshold: this.thresholds.latency.warning
      });
    }
    
    // Check audio quality thresholds
    if (metrics.audioQuality < this.thresholds.audioQuality.error) {
      alerts.push({
        id: `audio-${Date.now()}`,
        type: 'error',
        message: 'Poor audio quality detected - immediate attention required',
        timestamp: new Date().toISOString(),
        metric: 'audioQuality',
        value: metrics.audioQuality,
        threshold: this.thresholds.audioQuality.error
      });
    } else if (metrics.audioQuality < this.thresholds.audioQuality.warning) {
      alerts.push({
        id: `audio-${Date.now()}`,
        type: 'warning',
        message: 'Audio quality below optimal levels',
        timestamp: new Date().toISOString(),
        metric: 'audioQuality',
        value: metrics.audioQuality,
        threshold: this.thresholds.audioQuality.warning
      });
    }
    
    // Check escalation rate thresholds
    if (metrics.escalationRate > this.thresholds.escalationRate.error) {
      alerts.push({
        id: `escalation-${Date.now()}`,
        type: 'error',
        message: 'High escalation rate detected - review AI agent performance',
        timestamp: new Date().toISOString(),
        metric: 'escalationRate',
        value: metrics.escalationRate,
        threshold: this.thresholds.escalationRate.error
      });
    } else if (metrics.escalationRate > this.thresholds.escalationRate.warning) {
      alerts.push({
        id: `escalation-${Date.now()}`,
        type: 'warning',
        message: 'Escalation rate is above normal levels',
        timestamp: new Date().toISOString(),
        metric: 'escalationRate',
        value: metrics.escalationRate,
        threshold: this.thresholds.escalationRate.warning
      });
    }
    
    // Check sentiment thresholds
    if (metrics.sentimentScore < this.thresholds.sentiment.error) {
      alerts.push({
        id: `sentiment-${Date.now()}`,
        type: 'error',
        message: 'Very negative customer sentiment detected',
        timestamp: new Date().toISOString(),
        metric: 'sentimentScore',
        value: metrics.sentimentScore,
        threshold: this.thresholds.sentiment.error
      });
    } else if (metrics.sentimentScore < this.thresholds.sentiment.warning) {
      alerts.push({
        id: `sentiment-${Date.now()}`,
        type: 'warning',
        message: 'Customer sentiment trending negative',
        timestamp: new Date().toISOString(),
        metric: 'sentimentScore',
        value: metrics.sentimentScore,
        threshold: this.thresholds.sentiment.warning
      });
    }
    
    // Send alerts to clients
    for (const alert of alerts) {
      this.performanceAlerts.unshift(alert);
      this.broadcastToClients('performance_alert', { alert });
    }
    
    // Keep only last 100 alerts
    this.performanceAlerts = this.performanceAlerts.slice(0, 100);
  }

  public addClient(ws: WebSocket) {
    this.connectedClients.add(ws);
    
    // Send initial data to new client
    const initialData = {
      metrics: this.realtimeMetrics.slice(-50), // Last 50 data points
      sentiment: this.sentimentData.slice(-50),
      alerts: this.performanceAlerts.slice(0, 10)
    };
    
    ws.send(JSON.stringify({
      type: 'initial_data',
      data: initialData
    }));
    
    ws.on('close', () => {
      this.connectedClients.delete(ws);
    });
    
    ws.on('message', (message: any) => {
      try {
        const data = JSON.parse(message.toString());
        this.handleClientMessage(ws, data);
      } catch (error) {
        console.error('Error parsing client message:', error);
      }
    });
  }

  private handleClientMessage(ws: WebSocket, data: any) {
    switch (data.type) {
      case 'subscribe':
        // Client subscribing to specific channels
        break;
        
      case 'request_historical':
        this.sendHistoricalData(ws, data.timeRange);
        break;
        
      default:
        console.warn('Unknown client message type:', data.type);
    }
  }

  private async sendHistoricalData(ws: WebSocket, timeRange: string) {
    try {
      let interval: string;
      
      switch (timeRange) {
        case '1h':
          interval = '1 hour';
          break;
        case '6h':
          interval = '6 hours';
          break;
        case '24h':
          interval = '24 hours';
          break;
        case '7d':
          interval = '7 days';
          break;
        default:
          interval = '1 hour';
      }
      
      // Get historical metrics
      const metricsQuery = `
        SELECT 
          timestamp,
          active_conversations,
          average_latency,
          audio_quality,
          sentiment_score,
          escalation_rate,
          conversion_rate
        FROM analytics_snapshots 
        WHERE timestamp > NOW() - INTERVAL '${interval}'
        ORDER BY timestamp ASC
      `;
      
      const metricsResult = await this.db.query(metricsQuery);
      const historicalMetrics = metricsResult.rows.map(row => ({
        timestamp: row.timestamp,
        activeConversations: row.active_conversations,
        averageLatency: row.average_latency,
        audioQuality: row.audio_quality,
        sentimentScore: row.sentiment_score,
        escalationRate: row.escalation_rate,
        conversionRate: row.conversion_rate
      }));
      
      // Get historical sentiment data
      const sentimentQuery = `
        SELECT 
          created_at as timestamp,
          sentiment_score as sentiment,
          emotional_state,
          escalation_risk,
          confidence
        FROM conversation_turns 
        WHERE created_at > NOW() - INTERVAL '${interval}'
          AND sentiment_score IS NOT NULL
        ORDER BY created_at ASC
      `;
      
      const sentimentResult = await this.db.query(sentimentQuery);
      const historicalSentiment = sentimentResult.rows.map(row => ({
        timestamp: row.timestamp,
        sentiment: row.sentiment,
        emotionalState: row.emotional_state || 'neutral',
        escalationRisk: row.escalation_risk || 0,
        confidence: row.confidence || 0
      }));
      
      ws.send(JSON.stringify({
        type: 'historical_data',
        metrics: historicalMetrics,
        sentiment: historicalSentiment
      }));
      
    } catch (error) {
      console.error('Error sending historical data:', error);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Failed to retrieve historical data'
      }));
    }
  }

  private broadcastToClients(type: string, data: any) {
    const message = JSON.stringify({ type, ...data });
    
    this.connectedClients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(message);
        } catch (error) {
          console.error('Error sending message to client:', error);
          this.connectedClients.delete(client);
        }
      }
    });
  }

  public async saveMetricsSnapshot(metrics: ConversationMetrics) {
    try {
      const query = `
        INSERT INTO analytics_snapshots (
          timestamp, active_conversations, average_latency, audio_quality,
          sentiment_score, escalation_rate, conversion_rate
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
      `;
      
      await this.db.query(query, [
        metrics.timestamp,
        metrics.activeConversations,
        metrics.averageLatency,
        metrics.audioQuality,
        metrics.sentimentScore,
        metrics.escalationRate,
        metrics.conversionRate
      ]);
    } catch (error) {
      console.error('Error saving metrics snapshot:', error);
    }
  }

  public updateThresholds(newThresholds: Partial<typeof this.thresholds>) {
    this.thresholds = { ...this.thresholds, ...newThresholds };
    console.log('Updated performance thresholds:', this.thresholds);
  }

  public getConnectedClientsCount(): number {
    return this.connectedClients.size;
  }

  public cleanup() {
    if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
    }
    
    if (this.businessMetricsInterval) {
      clearInterval(this.businessMetricsInterval);
    }
    
    this.connectedClients.clear();
    this.redis.disconnect();
  }
}