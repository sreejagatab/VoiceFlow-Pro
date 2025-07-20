import { Router } from 'express'
import { z } from 'zod'
import { createLogger } from '../utils/logger.js'
import { DatabaseClient } from '../database/client.js'

const router = Router()
const logger = createLogger()
const db = new DatabaseClient()

// Schemas for validation
const conversationStateSchema = z.object({
  room_id: z.string(),
  participant_id: z.string(),
  name: z.string().optional(),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  current_scenario: z.enum(['onboarding', 'sales', 'support', 'scheduling', 'follow_up', 'escalation']),
  previous_scenarios: z.array(z.string()),
  lead_score: z.number().default(0),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  conversation_history: z.array(z.any()),
  extracted_entities: z.record(z.any()),
  business_actions: z.array(z.any()),
  sentiment_scores: z.array(z.number()),
  session_start: z.string(),
  last_activity: z.string()
})

const conversationMessageSchema = z.object({
  room_id: z.string(),
  speaker: z.enum(['customer', 'agent']),
  message: z.string(),
  metadata: z.record(z.any()),
  timestamp: z.string()
})

// Save conversation state
router.post('/state', async (req, res) => {
  try {
    const stateData = conversationStateSchema.parse(req.body)
    
    logger.info(`Saving conversation state for room ${stateData.room_id}`)
    
    // Insert or update customer record
    const customerId = await db.upsertCustomer({
      name: stateData.name,
      email: stateData.email,
      phone: stateData.phone,
      company: stateData.company
    })
    
    // Insert or update conversation record
    const conversationId = await db.upsertConversation({
      room_id: stateData.room_id,
      customer_id: customerId,
      scenario: stateData.current_scenario,
      status: 'active',
      started_at: new Date(stateData.session_start),
      total_words: stateData.conversation_history.length,
      sentiment_score: stateData.sentiment_scores.length > 0 
        ? stateData.sentiment_scores.reduce((a, b) => a + b) / stateData.sentiment_scores.length 
        : 0.0
    })
    
    // Save business actions
    for (const action of stateData.business_actions) {
      await db.insertBusinessAction({
        conversation_id: conversationId,
        action_type: action.type,
        action_data: action,
        status: 'completed'
      })
    }
    
    res.json({ 
      success: true, 
      conversation_id: conversationId,
      customer_id: customerId 
    })
    
  } catch (error) {
    logger.error('Error saving conversation state:', error)
    res.status(400).json({ 
      error: 'Failed to save conversation state',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Load conversation state
router.get('/state/:roomId', async (req, res) => {
  try {
    const { roomId } = req.params
    
    logger.info(`Loading conversation state for room ${roomId}`)
    
    const conversation = await db.getConversationByRoomId(roomId)
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' })
    }
    
    // Get customer details
    const customer = await db.getCustomerById(conversation.customer_id)
    
    // Get conversation messages
    const messages = await db.getConversationMessages(conversation.id)
    
    // Get business actions
    const actions = await db.getBusinessActions(conversation.id)
    
    // Reconstruct conversation state
    const conversationState = {
      room_id: roomId,
      participant_id: 'unknown', // Would need to track this separately
      name: customer?.name,
      email: customer?.email,
      phone: customer?.phone,
      company: customer?.company,
      current_scenario: conversation.scenario,
      previous_scenarios: [], // Would need to track this separately
      lead_score: 0, // Would need to calculate from actions
      priority: 'medium',
      conversation_history: messages.map(msg => ({
        speaker: msg.speaker,
        message: msg.message,
        timestamp: msg.timestamp,
        scenario: msg.metadata?.scenario || 'unknown'
      })),
      extracted_entities: {}, // Would need to aggregate from messages
      business_actions: actions.map(action => action.action_data),
      sentiment_scores: messages
        .filter(msg => msg.metadata?.sentiment)
        .map(msg => msg.metadata.sentiment),
      session_start: conversation.started_at.toISOString(),
      last_activity: new Date().toISOString()
    }
    
    res.json(conversationState)
    
  } catch (error) {
    logger.error('Error loading conversation state:', error)
    res.status(500).json({ 
      error: 'Failed to load conversation state',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Log conversation message
router.post('/message', async (req, res) => {
  try {
    const messageData = conversationMessageSchema.parse(req.body)
    
    logger.info(`Logging message for room ${messageData.room_id}`)
    
    // Get conversation ID from room ID
    const conversation = await db.getConversationByRoomId(messageData.room_id)
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' })
    }
    
    // Insert message
    await db.insertConversationMessage({
      conversation_id: conversation.id,
      speaker: messageData.speaker,
      message: messageData.message,
      transcript_confidence: messageData.metadata.confidence || null,
      timestamp: new Date(messageData.timestamp),
      metadata: messageData.metadata
    })
    
    res.json({ success: true })
    
  } catch (error) {
    logger.error('Error logging conversation message:', error)
    res.status(400).json({ 
      error: 'Failed to log message',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Get conversation analytics
router.get('/analytics/:roomId', async (req, res) => {
  try {
    const { roomId } = req.params
    
    const conversation = await db.getConversationByRoomId(roomId)
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' })
    }
    
    const messages = await db.getConversationMessages(conversation.id)
    const actions = await db.getBusinessActions(conversation.id)
    
    // Calculate analytics
    const totalWords = messages.reduce((total, msg) => 
      total + msg.message.split(' ').length, 0)
    
    const sentimentScores = messages
      .filter(msg => msg.metadata?.sentiment)
      .map(msg => msg.metadata.sentiment)
    
    const avgSentiment = sentimentScores.length > 0
      ? sentimentScores.reduce((a, b) => a + b) / sentimentScores.length
      : 0
    
    const scenarioTransitions = actions
      .filter(action => action.action_type === 'scenario_transition')
      .map(action => ({
        from: action.action_data.from,
        to: action.action_data.to,
        timestamp: action.action_data.timestamp
      }))
    
    const analytics = {
      room_id: roomId,
      duration: conversation.duration_seconds || 0,
      total_words: totalWords,
      message_count: messages.length,
      sentiment_score: avgSentiment,
      intent_confidence: 0.85, // Would calculate from actual intent detection
      scenario_transitions: scenarioTransitions,
      business_actions_count: actions.length,
      lead_score: 0, // Would calculate from sales actions
      support_tickets: actions.filter(a => a.action_type === 'support_ticket').length,
      appointments_scheduled: actions.filter(a => a.action_type === 'scheduling_request').length
    }
    
    res.json(analytics)
    
  } catch (error) {
    logger.error('Error getting analytics:', error)
    res.status(500).json({ 
      error: 'Failed to get analytics',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Get conversation summary for dashboard
router.get('/summary', async (req, res) => {
  try {
    const { limit = 10, offset = 0 } = req.query
    
    const conversations = await db.getRecentConversations(
      parseInt(limit as string), 
      parseInt(offset as string)
    )
    
    const summary = await Promise.all(conversations.map(async (conv) => {
      const customer = await db.getCustomerById(conv.customer_id)
      const messageCount = await db.getMessageCount(conv.id)
      const actionCount = await db.getActionCount(conv.id)
      
      return {
        id: conv.id,
        room_id: conv.room_id,
        customer_name: customer?.name || 'Unknown',
        customer_company: customer?.company,
        scenario: conv.scenario,
        status: conv.status,
        started_at: conv.started_at,
        duration: conv.duration_seconds,
        message_count: messageCount,
        action_count: actionCount,
        sentiment_score: conv.sentiment_score
      }
    }))
    
    res.json({
      conversations: summary,
      total: conversations.length,
      limit: parseInt(limit as string),
      offset: parseInt(offset as string)
    })
    
  } catch (error) {
    logger.error('Error getting conversation summary:', error)
    res.status(500).json({ 
      error: 'Failed to get conversation summary',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

export { router as conversationRoutes }