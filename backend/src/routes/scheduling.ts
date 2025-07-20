import { Router } from 'express'
import { z } from 'zod'
import { createLogger } from '../utils/logger.js'
import { GoogleCalendarService, CalendarEvent } from '../services/calendar.js'
import { DatabaseClient } from '../database/client.js'

const router = Router()
const logger = createLogger()
const calendarService = new GoogleCalendarService()
const db = new DatabaseClient()

// Validation schemas
const availabilityRequestSchema = z.object({
  days: z.number().min(1).max(30).default(7),
  duration: z.number().min(15).max(240).default(30),
  meetingType: z.enum(['demo', 'consultation', 'support', 'follow_up']),
  preferences: z.object({
    preferredDays: z.array(z.string()).optional(),
    preferredTimes: z.array(z.enum(['morning', 'afternoon', 'evening'])).optional(),
    excludeDates: z.array(z.string().datetime()).optional()
  }).optional()
})

const scheduleEventSchema = z.object({
  summary: z.string().min(1),
  description: z.string().optional(),
  startTime: z.string().datetime(),
  endTime: z.string().datetime(),
  attendeeEmail: z.string().email().optional(),
  attendeeName: z.string().optional(),
  meetingType: z.enum(['demo', 'consultation', 'support', 'follow_up']),
  roomId: z.string().optional(),
  customerData: z.object({
    name: z.string().optional(),
    email: z.string().email().optional(),
    phone: z.string().optional(),
    company: z.string().optional()
  }).optional()
})

const updateEventSchema = z.object({
  eventId: z.string(),
  summary: z.string().optional(),
  description: z.string().optional(),
  startTime: z.string().datetime().optional(),
  endTime: z.string().datetime().optional(),
  attendeeEmail: z.string().email().optional(),
  attendeeName: z.string().optional()
})

// Get available time slots
router.post('/availability', async (req, res) => {
  try {
    const { days, duration, meetingType, preferences } = availabilityRequestSchema.parse(req.body)
    
    logger.info(`Checking availability for ${meetingType} meetings`)
    
    let availableSlots
    
    if (preferences) {
      // Convert string dates to Date objects
      const processedPreferences = {
        ...preferences,
        excludeDates: preferences.excludeDates?.map(date => new Date(date)),
        durationMinutes: duration
      }
      
      availableSlots = await calendarService.findOptimalTimes(processedPreferences)
    } else {
      availableSlots = await calendarService.getAvailableSlots(days, duration)
    }
    
    // Format slots for response
    const formattedSlots = availableSlots.map(slot => ({
      startTime: slot.startTime.toISOString(),
      endTime: slot.endTime.toISOString(),
      duration: duration,
      displayTime: slot.startTime.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      })
    }))
    
    res.json({
      meetingType,
      duration,
      availableSlots: formattedSlots,
      totalSlots: formattedSlots.length
    })
    
  } catch (error) {
    logger.error('Error checking availability:', error)
    res.status(400).json({
      error: 'Failed to check availability',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Schedule a new event
router.post('/schedule', async (req, res) => {
  try {
    const eventData = scheduleEventSchema.parse(req.body)
    
    logger.info(`Scheduling ${eventData.meetingType} event`)
    
    // Prepare calendar event
    const calendarEvent: CalendarEvent = {
      summary: eventData.summary,
      description: eventData.description,
      startTime: new Date(eventData.startTime),
      endTime: new Date(eventData.endTime),
      attendeeEmail: eventData.attendeeEmail,
      attendeeName: eventData.attendeeName,
      meetingType: eventData.meetingType
    }
    
    // Schedule the event in Google Calendar
    const eventId = await calendarService.scheduleEvent(calendarEvent)
    
    if (!eventId) {
      return res.status(409).json({
        error: 'Time slot no longer available',
        message: 'The requested time slot has been booked by someone else'
      })
    }
    
    // Save to database if customer data provided
    let customerId: number | null = null
    let conversationId: number | null = null
    
    if (eventData.customerData && eventData.customerData.email) {
      customerId = await db.upsertCustomer(eventData.customerData)
      
      // If room ID provided, link to conversation
      if (eventData.roomId) {
        const conversation = await db.getConversationByRoomId(eventData.roomId)
        if (conversation) {
          conversationId = conversation.id
        } else {
          // Create conversation record for this scheduling
          conversationId = await db.upsertConversation({
            room_id: eventData.roomId,
            customer_id: customerId,
            scenario: 'scheduling',
            status: 'completed',
            started_at: new Date()
          })
        }
        
        // Record business action
        await db.insertBusinessAction({
          conversation_id: conversationId,
          action_type: 'appointment_scheduled',
          action_data: {
            calendar_event_id: eventId,
            meeting_type: eventData.meetingType,
            start_time: eventData.startTime,
            end_time: eventData.endTime,
            attendee_email: eventData.attendeeEmail,
            attendee_name: eventData.attendeeName
          },
          status: 'completed'
        })
      }
    }
    
    // Get the created event details
    const createdEvent = await calendarService.getEvent(eventId)
    
    res.json({
      success: true,
      eventId,
      customerId,
      conversationId,
      event: {
        id: eventId,
        summary: createdEvent?.summary,
        startTime: eventData.startTime,
        endTime: eventData.endTime,
        meetingLink: createdEvent?.hangoutLink || createdEvent?.conferenceData?.entryPoints?.[0]?.uri,
        attendees: createdEvent?.attendees?.map(a => ({
          email: a.email,
          name: a.displayName,
          responseStatus: a.responseStatus
        }))
      }
    })
    
  } catch (error) {
    logger.error('Error scheduling event:', error)
    res.status(400).json({
      error: 'Failed to schedule event',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Update an existing event
router.put('/update', async (req, res) => {
  try {
    const updateData = updateEventSchema.parse(req.body)
    
    logger.info(`Updating event ${updateData.eventId}`)
    
    const updates: Partial<CalendarEvent> = {}
    
    if (updateData.summary) updates.summary = updateData.summary
    if (updateData.description) updates.description = updateData.description
    if (updateData.startTime) updates.startTime = new Date(updateData.startTime)
    if (updateData.endTime) updates.endTime = new Date(updateData.endTime)
    if (updateData.attendeeEmail) updates.attendeeEmail = updateData.attendeeEmail
    if (updateData.attendeeName) updates.attendeeName = updateData.attendeeName
    
    const success = await calendarService.updateEvent(updateData.eventId, updates)
    
    if (!success) {
      return res.status(404).json({
        error: 'Event not found',
        message: 'The specified event could not be found or updated'
      })
    }
    
    res.json({ success: true, eventId: updateData.eventId })
    
  } catch (error) {
    logger.error('Error updating event:', error)
    res.status(400).json({
      error: 'Failed to update event',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Cancel an event
router.delete('/cancel/:eventId', async (req, res) => {
  try {
    const { eventId } = req.params
    
    logger.info(`Cancelling event ${eventId}`)
    
    const success = await calendarService.cancelEvent(eventId)
    
    if (!success) {
      return res.status(404).json({
        error: 'Event not found',
        message: 'The specified event could not be found or cancelled'
      })
    }
    
    // Update business action status if exists
    try {
      const result = await db.query(
        `UPDATE business_actions 
         SET status = 'cancelled' 
         WHERE action_data->>'calendar_event_id' = $1`,
        [eventId]
      )
      logger.info(`Updated ${result.rowCount} business action records`)
    } catch (dbError) {
      logger.warn('Could not update business action status:', dbError)
    }
    
    res.json({ success: true, eventId })
    
  } catch (error) {
    logger.error('Error cancelling event:', error)
    res.status(500).json({
      error: 'Failed to cancel event',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Get event details
router.get('/event/:eventId', async (req, res) => {
  try {
    const { eventId } = req.params
    
    const event = await calendarService.getEvent(eventId)
    
    if (!event) {
      return res.status(404).json({
        error: 'Event not found',
        message: 'The specified event could not be found'
      })
    }
    
    res.json({
      id: event.id,
      summary: event.summary,
      description: event.description,
      startTime: event.start?.dateTime,
      endTime: event.end?.dateTime,
      meetingLink: event.hangoutLink || event.conferenceData?.entryPoints?.[0]?.uri,
      attendees: event.attendees?.map(a => ({
        email: a.email,
        name: a.displayName,
        responseStatus: a.responseStatus
      })),
      status: event.status,
      created: event.created
    })
    
  } catch (error) {
    logger.error('Error getting event:', error)
    res.status(500).json({
      error: 'Failed to get event',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Get scheduling analytics
router.get('/analytics', async (req, res) => {
  try {
    const { days = 30 } = req.query
    
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - parseInt(days as string))
    
    // Get scheduling data from database
    const result = await db.query(
      `SELECT 
         COUNT(*) as total_appointments,
         COUNT(CASE WHEN action_data->>'meeting_type' = 'demo' THEN 1 END) as demos,
         COUNT(CASE WHEN action_data->>'meeting_type' = 'consultation' THEN 1 END) as consultations,
         COUNT(CASE WHEN action_data->>'meeting_type' = 'support' THEN 1 END) as support_sessions,
         COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
         COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
       FROM business_actions 
       WHERE action_type = 'appointment_scheduled' 
       AND created_at >= $1`,
      [startDate]
    )
    
    const analytics = result.rows[0]
    
    res.json({
      period: `${days} days`,
      appointments: {
        total: parseInt(analytics.total_appointments),
        demos: parseInt(analytics.demos),
        consultations: parseInt(analytics.consultations),
        support_sessions: parseInt(analytics.support_sessions)
      },
      status: {
        completed: parseInt(analytics.completed),
        cancelled: parseInt(analytics.cancelled),
        completion_rate: analytics.total_appointments > 0 
          ? (analytics.completed / analytics.total_appointments * 100).toFixed(2) + '%'
          : '0%'
      }
    })
    
  } catch (error) {
    logger.error('Error getting scheduling analytics:', error)
    res.status(500).json({
      error: 'Failed to get analytics',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

// Smart scheduling suggestions based on conversation context
router.post('/suggest', async (req, res) => {
  try {
    const { roomId, customerPreferences, urgency } = req.body
    
    // Get conversation context
    const conversation = await db.getConversationByRoomId(roomId)
    
    let meetingType: 'demo' | 'consultation' | 'support' | 'follow_up' = 'consultation'
    let duration = 30
    
    if (conversation) {
      // Determine meeting type based on conversation scenario
      switch (conversation.scenario) {
        case 'sales':
          meetingType = 'demo'
          duration = 45
          break
        case 'support':
          meetingType = 'support'
          duration = 60
          break
        case 'scheduling':
          meetingType = 'consultation'
          duration = 30
          break
        default:
          meetingType = 'consultation'
          duration = 30
      }
    }
    
    // Adjust for urgency
    const preferences: any = {
      durationMinutes: duration,
      preferredTimes: customerPreferences?.preferredTimes || ['morning', 'afternoon']
    }
    
    if (urgency === 'high') {
      // For urgent requests, look for next available slots
      preferences.preferredDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    }
    
    const suggestions = await calendarService.findOptimalTimes(preferences)
    
    res.json({
      meetingType,
      duration,
      urgency: urgency || 'normal',
      suggestions: suggestions.slice(0, 5).map(slot => ({
        startTime: slot.startTime.toISOString(),
        endTime: slot.endTime.toISOString(),
        displayTime: slot.startTime.toLocaleString('en-US', {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit'
        }),
        urgencyScore: urgency === 'high' ? 10 : 5
      }))
    })
    
  } catch (error) {
    logger.error('Error generating scheduling suggestions:', error)
    res.status(500).json({
      error: 'Failed to generate suggestions',
      message: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

export { router as schedulingRoutes }