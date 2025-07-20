import { Pool, PoolClient, QueryResult } from 'pg'
import { createLogger } from '../utils/logger.js'

const logger = createLogger()

export interface Customer {
  id: number
  name?: string
  email?: string
  phone?: string
  company?: string
  created_at: Date
  updated_at: Date
}

export interface Conversation {
  id: number
  room_id: string
  customer_id: number
  scenario: string
  status: string
  started_at: Date
  ended_at?: Date
  duration_seconds?: number
  total_words: number
  sentiment_score: number
}

export interface ConversationMessage {
  id: number
  conversation_id: number
  speaker: string
  message: string
  transcript_confidence?: number
  timestamp: Date
  metadata: any
}

export interface BusinessAction {
  id: number
  conversation_id: number
  action_type: string
  action_data: any
  status: string
  created_at: Date
  completed_at?: Date
}

export class DatabaseClient {
  private pool: Pool

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    })

    this.pool.on('error', (err) => {
      logger.error('Unexpected error on idle client', err)
    })
  }

  async query(text: string, params?: any[]): Promise<QueryResult> {
    const client = await this.pool.connect()
    try {
      const result = await client.query(text, params)
      return result
    } finally {
      client.release()
    }
  }

  async transaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
    const client = await this.pool.connect()
    try {
      await client.query('BEGIN')
      const result = await callback(client)
      await client.query('COMMIT')
      return result
    } catch (error) {
      await client.query('ROLLBACK')
      throw error
    } finally {
      client.release()
    }
  }

  // Customer operations
  async upsertCustomer(customerData: Partial<Customer>): Promise<number> {
    const { name, email, phone, company } = customerData

    if (email) {
      // Try to find existing customer by email
      const existingResult = await this.query(
        'SELECT id FROM customers WHERE email = $1',
        [email]
      )

      if (existingResult.rows.length > 0) {
        // Update existing customer
        await this.query(
          `UPDATE customers 
           SET name = COALESCE($1, name),
               phone = COALESCE($2, phone),
               company = COALESCE($3, company),
               updated_at = CURRENT_TIMESTAMP
           WHERE email = $4`,
          [name, phone, company, email]
        )
        return existingResult.rows[0].id
      }
    }

    // Create new customer
    const result = await this.query(
      `INSERT INTO customers (name, email, phone, company) 
       VALUES ($1, $2, $3, $4) 
       RETURNING id`,
      [name, email, phone, company]
    )

    return result.rows[0].id
  }

  async getCustomerById(id: number): Promise<Customer | null> {
    const result = await this.query(
      'SELECT * FROM customers WHERE id = $1',
      [id]
    )

    return result.rows.length > 0 ? result.rows[0] : null
  }

  async getCustomerByEmail(email: string): Promise<Customer | null> {
    const result = await this.query(
      'SELECT * FROM customers WHERE email = $1',
      [email]
    )

    return result.rows.length > 0 ? result.rows[0] : null
  }

  // Conversation operations
  async upsertConversation(conversationData: {
    room_id: string
    customer_id: number
    scenario: string
    status: string
    started_at: Date
    total_words?: number
    sentiment_score?: number
  }): Promise<number> {
    const { room_id, customer_id, scenario, status, started_at, total_words = 0, sentiment_score = 0.0 } = conversationData

    // Try to find existing conversation
    const existingResult = await this.query(
      'SELECT id FROM conversations WHERE room_id = $1',
      [room_id]
    )

    if (existingResult.rows.length > 0) {
      // Update existing conversation
      await this.query(
        `UPDATE conversations 
         SET scenario = $1,
             status = $2,
             total_words = $3,
             sentiment_score = $4
         WHERE room_id = $5`,
        [scenario, status, total_words, sentiment_score, room_id]
      )
      return existingResult.rows[0].id
    }

    // Create new conversation
    const result = await this.query(
      `INSERT INTO conversations (room_id, customer_id, scenario, status, started_at, total_words, sentiment_score) 
       VALUES ($1, $2, $3, $4, $5, $6, $7) 
       RETURNING id`,
      [room_id, customer_id, scenario, status, started_at, total_words, sentiment_score]
    )

    return result.rows[0].id
  }

  async getConversationByRoomId(roomId: string): Promise<Conversation | null> {
    const result = await this.query(
      'SELECT * FROM conversations WHERE room_id = $1',
      [roomId]
    )

    return result.rows.length > 0 ? result.rows[0] : null
  }

  async getConversationById(id: number): Promise<Conversation | null> {
    const result = await this.query(
      'SELECT * FROM conversations WHERE id = $1',
      [id]
    )

    return result.rows.length > 0 ? result.rows[0] : null
  }

  async endConversation(roomId: string, durationSeconds: number): Promise<void> {
    await this.query(
      `UPDATE conversations 
       SET ended_at = CURRENT_TIMESTAMP,
           duration_seconds = $1,
           status = 'completed'
       WHERE room_id = $2`,
      [durationSeconds, roomId]
    )
  }

  async getRecentConversations(limit: number = 10, offset: number = 0): Promise<Conversation[]> {
    const result = await this.query(
      `SELECT * FROM conversations 
       ORDER BY started_at DESC 
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    )

    return result.rows
  }

  // Message operations
  async insertConversationMessage(messageData: {
    conversation_id: number
    speaker: string
    message: string
    transcript_confidence?: number
    timestamp: Date
    metadata: any
  }): Promise<number> {
    const { conversation_id, speaker, message, transcript_confidence, timestamp, metadata } = messageData

    const result = await this.query(
      `INSERT INTO conversation_messages (conversation_id, speaker, message, transcript_confidence, timestamp, metadata) 
       VALUES ($1, $2, $3, $4, $5, $6) 
       RETURNING id`,
      [conversation_id, speaker, message, transcript_confidence, timestamp, JSON.stringify(metadata)]
    )

    return result.rows[0].id
  }

  async getConversationMessages(conversationId: number): Promise<ConversationMessage[]> {
    const result = await this.query(
      `SELECT * FROM conversation_messages 
       WHERE conversation_id = $1 
       ORDER BY timestamp ASC`,
      [conversationId]
    )

    return result.rows.map(row => ({
      ...row,
      metadata: typeof row.metadata === 'string' ? JSON.parse(row.metadata) : row.metadata
    }))
  }

  async getMessageCount(conversationId: number): Promise<number> {
    const result = await this.query(
      'SELECT COUNT(*) as count FROM conversation_messages WHERE conversation_id = $1',
      [conversationId]
    )

    return parseInt(result.rows[0].count)
  }

  // Business action operations
  async insertBusinessAction(actionData: {
    conversation_id: number
    action_type: string
    action_data: any
    status: string
  }): Promise<number> {
    const { conversation_id, action_type, action_data, status } = actionData

    const result = await this.query(
      `INSERT INTO business_actions (conversation_id, action_type, action_data, status) 
       VALUES ($1, $2, $3, $4) 
       RETURNING id`,
      [conversation_id, action_type, JSON.stringify(action_data), status]
    )

    return result.rows[0].id
  }

  async getBusinessActions(conversationId: number): Promise<BusinessAction[]> {
    const result = await this.query(
      `SELECT * FROM business_actions 
       WHERE conversation_id = $1 
       ORDER BY created_at ASC`,
      [conversationId]
    )

    return result.rows.map(row => ({
      ...row,
      action_data: typeof row.action_data === 'string' ? JSON.parse(row.action_data) : row.action_data
    }))
  }

  async getActionCount(conversationId: number): Promise<number> {
    const result = await this.query(
      'SELECT COUNT(*) as count FROM business_actions WHERE conversation_id = $1',
      [conversationId]
    )

    return parseInt(result.rows[0].count)
  }

  async completeBusinessAction(actionId: number): Promise<void> {
    await this.query(
      `UPDATE business_actions 
       SET status = 'completed', completed_at = CURRENT_TIMESTAMP 
       WHERE id = $1`,
      [actionId]
    )
  }

  // Analytics operations
  async getAgentMetrics(date: Date): Promise<any> {
    const result = await this.query(
      `SELECT 
         COUNT(*) as total_conversations,
         AVG(duration_seconds) as avg_conversation_duration,
         AVG(sentiment_score) as avg_sentiment_score,
         COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_conversions,
         COUNT(CASE WHEN scenario = 'escalation' THEN 1 END) as escalations
       FROM conversations 
       WHERE DATE(started_at) = $1`,
      [date.toISOString().split('T')[0]]
    )

    return result.rows[0]
  }

  async updateAgentMetrics(date: Date): Promise<void> {
    const metrics = await this.getAgentMetrics(date)

    await this.query(
      `INSERT INTO agent_metrics (date, total_conversations, avg_conversation_duration, avg_sentiment_score, successful_conversions, escalations)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (date) DO UPDATE SET
         total_conversations = EXCLUDED.total_conversations,
         avg_conversation_duration = EXCLUDED.avg_conversation_duration,
         avg_sentiment_score = EXCLUDED.avg_sentiment_score,
         successful_conversions = EXCLUDED.successful_conversions,
         escalations = EXCLUDED.escalations`,
      [
        date.toISOString().split('T')[0],
        metrics.total_conversations,
        metrics.avg_conversation_duration,
        metrics.avg_sentiment_score,
        metrics.successful_conversions,
        metrics.escalations
      ]
    )
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      await this.query('SELECT 1')
      return true
    } catch (error) {
      logger.error('Database health check failed:', error)
      return false
    }
  }

  async close(): Promise<void> {
    await this.pool.end()
  }
}