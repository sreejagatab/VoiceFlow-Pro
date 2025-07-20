-- VoiceFlow Pro Database Schema

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    company VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(255) NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    scenario VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    total_words INTEGER DEFAULT 0,
    sentiment_score FLOAT DEFAULT 0.0
);

-- Conversation messages table
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    speaker VARCHAR(50) NOT NULL, -- 'customer' or 'agent'
    message TEXT NOT NULL,
    transcript_confidence FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Business actions table (lead captures, appointments, etc.)
CREATE TABLE business_actions (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    action_type VARCHAR(100) NOT NULL, -- 'lead_capture', 'appointment_scheduled', 'ticket_created'
    action_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent performance metrics
CREATE TABLE agent_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_conversations INTEGER DEFAULT 0,
    avg_conversation_duration FLOAT DEFAULT 0.0,
    avg_sentiment_score FLOAT DEFAULT 0.0,
    successful_conversions INTEGER DEFAULT 0,
    escalations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_conversations_room_id ON conversations(room_id);
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_started_at ON conversations(started_at);
CREATE INDEX idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX idx_conversation_messages_timestamp ON conversation_messages(timestamp);
CREATE INDEX idx_business_actions_conversation_id ON business_actions(conversation_id);
CREATE INDEX idx_business_actions_action_type ON business_actions(action_type);
CREATE INDEX idx_agent_metrics_date ON agent_metrics(date);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();