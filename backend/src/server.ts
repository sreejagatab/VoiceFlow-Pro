import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import dotenv from 'dotenv'
import cron from 'node-cron'
import { createLogger } from './utils/logger.js'
import { livekitRoutes } from './routes/livekit.js'
import { agentRoutes } from './routes/agent.js'
import { conversationRoutes } from './routes/conversation.js'
import { schedulingRoutes } from './routes/scheduling.js'
import { DatabaseClient } from './database/client.js'

dotenv.config()

const app = express()
const port = process.env.PORT || 8000
const logger = createLogger()
const db = new DatabaseClient()

// Middleware
app.use(helmet())
app.use(cors({
  origin: process.env.NODE_ENV === 'production' 
    ? ['https://your-domain.com'] 
    : ['http://localhost:3000', 'http://127.0.0.1:3000']
}))
app.use(express.json())

// Request logging
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent')
  })
  next()
})

// Routes
app.use('/api/livekit', livekitRoutes)
app.use('/api/agent', agentRoutes)
app.use('/api/conversation', conversationRoutes)
app.use('/api/scheduling', schedulingRoutes)

// Health check with database connectivity
app.get('/health', async (req, res) => {
  try {
    const dbHealthy = await db.healthCheck()
    
    res.json({ 
      status: 'healthy', 
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      services: {
        database: dbHealthy ? 'healthy' : 'unhealthy',
        livekit: 'healthy', // Would implement actual LiveKit health check
        calendar: 'healthy' // Would implement actual Calendar API health check
      }
    })
  } catch (error) {
    logger.error('Health check failed:', error)
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// LiveKit webhook endpoint
app.post('/api/webhook/livekit', (req, res) => {
  const event = req.body
  
  logger.info('LiveKit webhook received:', { 
    event: event.event,
    room: event.room?.name,
    participant: event.participant?.identity 
  })
  
  // Handle different LiveKit events
  switch (event.event) {
    case 'room_started':
      logger.info(`Room started: ${event.room.name}`)
      break
    
    case 'room_finished':
      logger.info(`Room finished: ${event.room.name}`)
      // Update conversation end time in database
      handleRoomFinished(event.room)
      break
    
    case 'participant_joined':
      logger.info(`Participant joined: ${event.participant.identity} in ${event.room.name}`)
      break
    
    case 'participant_left':
      logger.info(`Participant left: ${event.participant.identity} in ${event.room.name}`)
      break
    
    case 'track_published':
      logger.info(`Track published: ${event.track.type} by ${event.participant.identity}`)
      break
  }
  
  res.json({ received: true })
})

// Background task to update agent metrics daily
cron.schedule('0 0 * * *', async () => {
  try {
    logger.info('Running daily agent metrics update')
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    
    await db.updateAgentMetrics(yesterday)
    logger.info('Agent metrics updated successfully')
  } catch (error) {
    logger.error('Failed to update agent metrics:', error)
  }
})

// Background task to clean up old conversation data (weekly)
cron.schedule('0 2 * * 0', async () => {
  try {
    logger.info('Running weekly cleanup of old conversation data')
    
    // Delete conversations older than 90 days
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - 90)
    
    const result = await db.query(
      'DELETE FROM conversations WHERE started_at < $1',
      [cutoffDate]
    )
    
    logger.info(`Cleaned up ${result.rowCount} old conversations`)
  } catch (error) {
    logger.error('Failed to clean up old data:', error)
  }
})

async function handleRoomFinished(room: any) {
  try {
    // Calculate room duration and update conversation
    const conversation = await db.getConversationByRoomId(room.name)
    
    if (conversation && conversation.started_at) {
      const endTime = new Date()
      const durationSeconds = Math.floor(
        (endTime.getTime() - conversation.started_at.getTime()) / 1000
      )
      
      await db.endConversation(room.name, durationSeconds)
      logger.info(`Updated conversation duration: ${durationSeconds}s for room ${room.name}`)
    }
  } catch (error) {
    logger.error('Error handling room finished event:', error)
  }
}

// Error handling
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logger.error('Unhandled error:', err)
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  })
})

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully')
  
  try {
    await db.close()
    logger.info('Database connections closed')
  } catch (error) {
    logger.error('Error closing database:', error)
  }
  
  process.exit(0)
})

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully')
  
  try {
    await db.close()
    logger.info('Database connections closed')
  } catch (error) {
    logger.error('Error closing database:', error)
  }
  
  process.exit(0)
})

app.listen(port, () => {
  logger.info(`VoiceFlow Pro backend running on port ${port}`)
  logger.info(`Environment: ${process.env.NODE_ENV}`)
  logger.info(`Database: ${process.env.DATABASE_URL ? 'configured' : 'not configured'}`)
  logger.info(`LiveKit: ${process.env.LIVEKIT_URL || 'not configured'}`)
})