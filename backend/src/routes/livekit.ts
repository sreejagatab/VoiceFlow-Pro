import { Router } from 'express'
import { AccessToken, RoomServiceClient } from 'livekit-server-sdk'
import { z } from 'zod'
import { createLogger } from '../utils/logger.js'

const router = Router()
const logger = createLogger()

const tokenRequestSchema = z.object({
  room: z.string().min(1),
  username: z.string().min(1),
  metadata: z.record(z.string()).optional()
})

// LiveKit room service client
const roomService = new RoomServiceClient(
  process.env.LIVEKIT_URL!,
  process.env.LIVEKIT_API_KEY!,
  process.env.LIVEKIT_SECRET_KEY!
)

// Generate access token for LiveKit room
router.post('/token', async (req, res) => {
  try {
    const { room, username, metadata } = tokenRequestSchema.parse(req.body)
    
    // Create access token
    const at = new AccessToken(
      process.env.LIVEKIT_API_KEY!,
      process.env.LIVEKIT_SECRET_KEY!,
      {
        identity: username,
        metadata: JSON.stringify(metadata || {})
      }
    )
    
    // Grant permissions
    at.addGrant({
      room,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true
    })
    
    const token = await at.toJwt()
    
    logger.info(`Generated token for user ${username} in room ${room}`)
    
    res.json({
      token,
      room,
      username,
      livekit_url: process.env.LIVEKIT_URL
    })
    
  } catch (error) {
    logger.error('Token generation error:', error)
    res.status(400).json({ 
      error: 'Invalid request',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Create or get room information
router.post('/room', async (req, res) => {
  try {
    const { room } = z.object({ room: z.string() }).parse(req.body)
    
    // Create room if it doesn't exist
    const roomInfo = await roomService.createRoom({
      name: room,
      emptyTimeout: 300, // 5 minutes
      maxParticipants: 10
    })
    
    logger.info(`Room created/retrieved: ${room}`)
    
    res.json(roomInfo)
    
  } catch (error) {
    logger.error('Room creation error:', error)
    res.status(500).json({ 
      error: 'Failed to create room',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// List active rooms
router.get('/rooms', async (req, res) => {
  try {
    const rooms = await roomService.listRooms()
    res.json(rooms)
  } catch (error) {
    logger.error('List rooms error:', error)
    res.status(500).json({ 
      error: 'Failed to list rooms',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

export { router as livekitRoutes }