import { google, calendar_v3 } from 'googleapis'
import { OAuth2Client } from 'google-auth-library'
import { createLogger } from '../utils/logger.js'

const logger = createLogger()

export interface CalendarEvent {
  id?: string
  summary: string
  description?: string
  startTime: Date
  endTime: Date
  attendeeEmail?: string
  attendeeName?: string
  meetingType: 'demo' | 'consultation' | 'support' | 'follow_up'
}

export interface AvailabilitySlot {
  startTime: Date
  endTime: Date
  isAvailable: boolean
}

export class GoogleCalendarService {
  private calendar: calendar_v3.Calendar
  private oauth2Client: OAuth2Client
  private calendarId: string

  constructor() {
    // Initialize OAuth2 client
    this.oauth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI
    )

    // Set credentials if available
    if (process.env.GOOGLE_REFRESH_TOKEN) {
      this.oauth2Client.setCredentials({
        refresh_token: process.env.GOOGLE_REFRESH_TOKEN,
        access_token: process.env.GOOGLE_ACCESS_TOKEN,
      })
    }

    this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client })
    this.calendarId = process.env.GOOGLE_CALENDAR_ID || 'primary'
  }

  /**
   * Check availability for a specific time range
   */
  async checkAvailability(startTime: Date, endTime: Date): Promise<boolean> {
    try {
      const response = await this.calendar.freebusy.query({
        requestBody: {
          timeMin: startTime.toISOString(),
          timeMax: endTime.toISOString(),
          items: [{ id: this.calendarId }]
        }
      })

      const busy = response.data.calendars?.[this.calendarId]?.busy || []
      
      // Check if the requested time conflicts with any busy periods
      return !busy.some(busyPeriod => {
        const busyStart = new Date(busyPeriod.start!)
        const busyEnd = new Date(busyPeriod.end!)
        
        return (
          (startTime >= busyStart && startTime < busyEnd) ||
          (endTime > busyStart && endTime <= busyEnd) ||
          (startTime <= busyStart && endTime >= busyEnd)
        )
      })
    } catch (error) {
      logger.error('Error checking calendar availability:', error)
      return false
    }
  }

  /**
   * Get available time slots for the next N days
   */
  async getAvailableSlots(days: number = 7, durationMinutes: number = 30): Promise<AvailabilitySlot[]> {
    const slots: AvailabilitySlot[] = []
    const now = new Date()
    
    // Business hours: 9 AM to 5 PM, Monday to Friday
    const businessHours = {
      start: 9, // 9 AM
      end: 17,  // 5 PM
      weekdays: [1, 2, 3, 4, 5] // Monday to Friday
    }

    for (let i = 0; i < days; i++) {
      const date = new Date(now)
      date.setDate(date.getDate() + i)
      
      // Skip weekends
      if (!businessHours.weekdays.includes(date.getDay())) {
        continue
      }

      // Generate slots for business hours
      for (let hour = businessHours.start; hour < businessHours.end; hour++) {
        for (let minute = 0; minute < 60; minute += durationMinutes) {
          const slotStart = new Date(date)
          slotStart.setHours(hour, minute, 0, 0)
          
          const slotEnd = new Date(slotStart)
          slotEnd.setMinutes(slotStart.getMinutes() + durationMinutes)

          // Skip past time slots
          if (slotStart <= now) {
            continue
          }

          const isAvailable = await this.checkAvailability(slotStart, slotEnd)
          
          slots.push({
            startTime: slotStart,
            endTime: slotEnd,
            isAvailable
          })
        }
      }
    }

    return slots.filter(slot => slot.isAvailable)
  }

  /**
   * Schedule a new calendar event
   */
  async scheduleEvent(eventData: CalendarEvent): Promise<string | null> {
    try {
      // Check availability first
      const isAvailable = await this.checkAvailability(eventData.startTime, eventData.endTime)
      
      if (!isAvailable) {
        logger.warn('Attempted to schedule event during busy time')
        return null
      }

      // Prepare event details
      const event: calendar_v3.Schema$Event = {
        summary: eventData.summary,
        description: this.generateEventDescription(eventData),
        start: {
          dateTime: eventData.startTime.toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        },
        end: {
          dateTime: eventData.endTime.toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        },
        attendees: eventData.attendeeEmail ? [
          {
            email: eventData.attendeeEmail,
            displayName: eventData.attendeeName
          }
        ] : undefined,
        conferenceData: {
          createRequest: {
            requestId: `voiceflow-${Date.now()}`,
            conferenceSolutionKey: {
              type: 'hangoutsMeet'
            }
          }
        },
        reminders: {
          useDefault: false,
          overrides: [
            { method: 'email', minutes: 60 },
            { method: 'popup', minutes: 15 }
          ]
        }
      }

      const response = await this.calendar.events.insert({
        calendarId: this.calendarId,
        requestBody: event,
        conferenceDataVersion: 1,
        sendUpdates: 'all'
      })

      logger.info(`Scheduled event: ${response.data.id}`)
      return response.data.id || null

    } catch (error) {
      logger.error('Error scheduling calendar event:', error)
      return null
    }
  }

  /**
   * Update an existing calendar event
   */
  async updateEvent(eventId: string, updates: Partial<CalendarEvent>): Promise<boolean> {
    try {
      const existingEvent = await this.calendar.events.get({
        calendarId: this.calendarId,
        eventId
      })

      if (!existingEvent.data) {
        return false
      }

      const updatedEvent: calendar_v3.Schema$Event = {
        ...existingEvent.data,
        summary: updates.summary || existingEvent.data.summary,
        description: updates.description || existingEvent.data.description,
        start: updates.startTime ? {
          dateTime: updates.startTime.toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        } : existingEvent.data.start,
        end: updates.endTime ? {
          dateTime: updates.endTime.toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        } : existingEvent.data.end
      }

      await this.calendar.events.update({
        calendarId: this.calendarId,
        eventId,
        requestBody: updatedEvent,
        sendUpdates: 'all'
      })

      logger.info(`Updated event: ${eventId}`)
      return true

    } catch (error) {
      logger.error('Error updating calendar event:', error)
      return false
    }
  }

  /**
   * Cancel a calendar event
   */
  async cancelEvent(eventId: string): Promise<boolean> {
    try {
      await this.calendar.events.delete({
        calendarId: this.calendarId,
        eventId,
        sendUpdates: 'all'
      })

      logger.info(`Cancelled event: ${eventId}`)
      return true

    } catch (error) {
      logger.error('Error cancelling calendar event:', error)
      return false
    }
  }

  /**
   * Get event details
   */
  async getEvent(eventId: string): Promise<calendar_v3.Schema$Event | null> {
    try {
      const response = await this.calendar.events.get({
        calendarId: this.calendarId,
        eventId
      })

      return response.data
    } catch (error) {
      logger.error('Error getting calendar event:', error)
      return null
    }
  }

  /**
   * Find optimal meeting times based on preferences
   */
  async findOptimalTimes(
    preferences: {
      preferredDays?: string[]
      preferredTimes?: string[]
      durationMinutes: number
      excludeDates?: Date[]
    }
  ): Promise<AvailabilitySlot[]> {
    const allSlots = await this.getAvailableSlots(14, preferences.durationMinutes)
    
    return allSlots.filter(slot => {
      // Filter by preferred days if specified
      if (preferences.preferredDays && preferences.preferredDays.length > 0) {
        const dayName = slot.startTime.toLocaleDateString('en-US', { weekday: 'long' })
        if (!preferences.preferredDays.includes(dayName)) {
          return false
        }
      }

      // Filter by preferred times if specified
      if (preferences.preferredTimes && preferences.preferredTimes.length > 0) {
        const hour = slot.startTime.getHours()
        const timeCategory = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'
        if (!preferences.preferredTimes.includes(timeCategory)) {
          return false
        }
      }

      // Exclude specific dates if provided
      if (preferences.excludeDates && preferences.excludeDates.length > 0) {
        const slotDate = slot.startTime.toDateString()
        if (preferences.excludeDates.some(date => date.toDateString() === slotDate)) {
          return false
        }
      }

      return true
    }).slice(0, 10) // Return top 10 options
  }

  /**
   * Generate meeting description based on type
   */
  private generateEventDescription(eventData: CalendarEvent): string {
    const baseDescription = `
Scheduled via VoiceFlow Pro Business Automation

Meeting Type: ${eventData.meetingType.charAt(0).toUpperCase() + eventData.meetingType.slice(1)}
    `.trim()

    const typeSpecificDetails = {
      demo: `
This is a personalized product demonstration where we'll show you how VoiceFlow Pro can streamline your business operations. We'll cover:
- Key features and capabilities
- Integration options
- Pricing and packages
- Q&A session

Please prepare any specific questions about your use case.`,
      
      consultation: `
This consultation will help us understand your specific business needs and requirements. We'll discuss:
- Current challenges and pain points
- Technical requirements
- Implementation timeline
- Custom solution options

Please have information about your current systems ready.`,
      
      support: `
This is a technical support session to help resolve your issues. We'll:
- Review the reported problem in detail
- Provide troubleshooting steps
- Implement solutions
- Ensure everything is working properly

Please have access to your system available during the call.`,
      
      follow_up: `
This follow-up session will review progress and next steps:
- Check on previous action items
- Address any new questions
- Plan next phases
- Ensure satisfaction

We'll reference our previous conversations and commitments.`
    }

    return `${baseDescription}\n\n${typeSpecificDetails[eventData.meetingType]}`
  }

  /**
   * Generate OAuth2 authorization URL for initial setup
   */
  getAuthUrl(): string {
    const scopes = [
      'https://www.googleapis.com/auth/calendar',
      'https://www.googleapis.com/auth/calendar.events'
    ]

    return this.oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: scopes,
      prompt: 'consent'
    })
  }

  /**
   * Exchange authorization code for tokens
   */
  async exchangeCodeForTokens(code: string): Promise<any> {
    try {
      const { tokens } = await this.oauth2Client.getToken(code)
      this.oauth2Client.setCredentials(tokens)
      return tokens
    } catch (error) {
      logger.error('Error exchanging code for tokens:', error)
      throw error
    }
  }
}