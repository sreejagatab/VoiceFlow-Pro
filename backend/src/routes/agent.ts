import { Router } from 'express'
import { z } from 'zod'
import { createLogger } from '../utils/logger.js'

const router = Router()
const logger = createLogger()

const conversationSchema = z.object({
  transcript: z.string(),
  context: z.object({
    scenario: z.enum(['sales', 'support', 'scheduling']),
    customer_info: z.record(z.any()).optional(),
    conversation_history: z.array(z.object({
      speaker: z.enum(['user', 'agent']),
      message: z.string(),
      timestamp: z.string()
    })).optional()
  })
})

// Process conversation and generate agent response
router.post('/conversation', async (req, res) => {
  try {
    const { transcript, context } = conversationSchema.parse(req.body)
    
    logger.info(`Processing conversation for scenario: ${context.scenario}`)
    
    // This would integrate with OpenAI/Claude for response generation
    // For now, return a mock response based on scenario
    const response = generateMockResponse(transcript, context.scenario)
    
    res.json({
      response: response.text,
      actions: response.actions,
      next_scenario: response.nextScenario,
      confidence: response.confidence
    })
    
  } catch (error) {
    logger.error('Conversation processing error:', error)
    res.status(400).json({ 
      error: 'Invalid conversation request',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Get conversation analytics
router.get('/analytics/:roomId', async (req, res) => {
  try {
    const { roomId } = req.params
    
    // Mock analytics data
    const analytics = {
      room_id: roomId,
      duration: 120, // seconds
      total_words: 245,
      sentiment_score: 0.7,
      intent_confidence: 0.85,
      scenario_transitions: [
        { from: 'sales', to: 'scheduling', timestamp: '2024-01-15T10:30:00Z' }
      ]
    }
    
    res.json(analytics)
    
  } catch (error) {
    logger.error('Analytics error:', error)
    res.status(500).json({ 
      error: 'Failed to get analytics',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

function generateMockResponse(transcript: string, scenario: string) {
  const responses = {
    sales: {
      text: "I understand you're interested in our enterprise solution. Let me gather some information about your current setup to recommend the best package for your needs.",
      actions: ['log_lead', 'schedule_demo'],
      nextScenario: 'scheduling',
      confidence: 0.9
    },
    support: {
      text: "I see you're experiencing technical issues. Let me escalate this to our technical team immediately. I'm creating a priority ticket for you.",
      actions: ['create_ticket', 'escalate_to_tech'],
      nextScenario: 'support',
      confidence: 0.85
    },
    scheduling: {
      text: "I can help you schedule that appointment. I have availability next Tuesday morning or Wednesday afternoon. Which works better for you?",
      actions: ['check_calendar', 'propose_times'],
      nextScenario: 'scheduling',
      confidence: 0.8
    }
  }
  
  return responses[scenario as keyof typeof responses] || responses.sales
}

export { router as agentRoutes }