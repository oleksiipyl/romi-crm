# AI Lead Responder — PostgreSQL Data Model

> **Module:** ROMI CRM Module 10  
> **Date:** 2026-06-14  
> **Extends:** `docs/ARCHITECTURE.md` core schema

---

## Overview

New tables prefixed with `ai_` to namespace Module 10. All tables reference existing `contacts` and `leads` tables. Uses `pgvector` for RAG embeddings.

**Migration file (future):** `backend/migrations/010_ai_responder.sql`

---

## Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│  contacts   │◄──────│  ai_conversations │──────►│     leads       │
│  (existing) │       │                  │       │   (existing)    │
└─────────────┘       └────────┬─────────┘       └─────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ ai_messages  │  │ ai_callbacks │  │ai_channel_   │
     │              │  │              │  │  events      │
     └──────────────┘  └──────────────┘  └──────────────┘

┌─────────────────┐       ┌──────────────────┐
│  kb_documents   │──────►│   kb_chunks      │
│                 │       │  (pgvector)      │
└─────────────────┘       └──────────────────┘

┌─────────────────┐       ┌──────────────────┐
│ ai_bot_config   │       │ ai_analytics_    │
│ (persona)       │       │   daily          │
└─────────────────┘       └──────────────────┘
```

---

## Table Definitions

### `ai_conversations`

Central conversation record — one per lead per channel thread.

```sql
CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID NOT NULL REFERENCES contacts(id),
    lead_id         UUID REFERENCES leads(id),
    
    -- Channel
    channel         VARCHAR(30) NOT NULL,
    -- 'yelp_raq' | 'website_widget' | 'sms' | 'voice' | 'thumbtack' | 'google_lsa'
    channel_thread_id VARCHAR(255),
    -- External ID: yelp_lead_id, twilio_conversation_sid, widget_session_id
    
    -- State machine
    state           VARCHAR(30) NOT NULL DEFAULT 'greet',
    -- 'idle' | 'greet' | 'qualify' | 'offer' | 'close' | 'callback' | 
    -- 'voice_active' | 'human_active' | 'complete' | 'retry_sms' | 'follow_up_queued'
    previous_state  VARCHAR(30),
    
    -- Control
    ai_enabled      BOOLEAN NOT NULL DEFAULT true,
    -- false when human has taken over
    assigned_to     UUID REFERENCES users(id),
    -- human agent if taken over
    
    -- Context (denormalized for fast access)
    service_id      VARCHAR(100),
    price_quoted_min DECIMAL(10,2),
    price_quoted_max DECIMAL(10,2),
    zip_code        VARCHAR(10),
    consent_callback BOOLEAN DEFAULT false,
    consent_callback_at TIMESTAMPTZ,
    
    -- Timing
    first_response_at   TIMESTAMPTZ,
    -- NULL until AI sends first message (for speed-to-lead KPI)
    last_message_at     TIMESTAMPTZ,
    last_ai_message_at  TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    
    -- Outcome
    outcome         VARCHAR(30),
    -- 'booked' | 'callback_completed' | 'handoff' | 'no_response' | 'out_of_zone' | 'spam'
    outcome_detail  JSONB,
    
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    -- channel-specific data: yelp_project_survey, widget_page_url, etc.
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_conversations_contact ON ai_conversations(contact_id);
CREATE INDEX idx_ai_conversations_lead ON ai_conversations(lead_id);
CREATE INDEX idx_ai_conversations_state ON ai_conversations(state) WHERE state NOT IN ('complete', 'idle');
CREATE INDEX idx_ai_conversations_channel ON ai_conversations(channel, channel_thread_id);
CREATE INDEX idx_ai_conversations_active ON ai_conversations(ai_enabled, last_message_at DESC) 
    WHERE ai_enabled = true AND state NOT IN ('complete', 'idle');
```

---

### `ai_messages`

Every message in a conversation — inbound, outbound, system, voice transcript.

```sql
CREATE TABLE ai_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    
    -- Direction
    direction       VARCHAR(10) NOT NULL,
    -- 'inbound' | 'outbound' | 'system'
    sender_type     VARCHAR(10) NOT NULL,
    -- 'lead' | 'ai' | 'human' | 'system'
    sender_id       UUID,
    -- users.id if human; NULL if AI or lead
    
    -- Content
    channel         VARCHAR(30) NOT NULL,
    -- same enum as ai_conversations.channel; 'voice' for call transcripts
    content_type    VARCHAR(20) NOT NULL DEFAULT 'text',
    -- 'text' | 'image' | 'audio' | 'transcript' | 'tool_call' | 'tool_result'
    body            TEXT,
    
    -- Tool calling (OpenAI function calls)
    tool_name       VARCHAR(100),
    tool_args       JSONB,
    tool_result     JSONB,
    
    -- Voice-specific
    call_id         UUID REFERENCES ai_callbacks(id),
    audio_url       VARCHAR(500),
    -- Twilio/Retell recording URL
    duration_ms     INTEGER,
    
    -- External refs
    external_id     VARCHAR(255),
    -- twilio_message_sid, yelp_message_id, retell_utterance_id
    
    -- AI metadata
    model           VARCHAR(50),
    -- 'gpt-4.1', 'gpt-4.1-mini', 'retell-llm'
    tokens_input    INTEGER,
    tokens_output   INTEGER,
    latency_ms      INTEGER,
    
    -- State at time of message
    conversation_state VARCHAR(30),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);
CREATE INDEX idx_ai_messages_external ON ai_messages(external_id) WHERE external_id IS NOT NULL;
```

---

### `ai_callbacks`

Voice callback attempts — links to Retell/Twilio call records.

```sql
CREATE TABLE ai_callbacks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id),
    contact_id      UUID NOT NULL REFERENCES contacts(id),
    
    -- Phone
    to_number       VARCHAR(20) NOT NULL,
    from_number     VARCHAR(20) NOT NULL,
    
    -- Provider
    provider        VARCHAR(20) NOT NULL DEFAULT 'retell',
    -- 'retell' | 'twilio' | 'vapi'
    provider_call_id VARCHAR(255),
    -- retell call_id or twilio CallSid
    
    -- Scheduling
    scheduled_at    TIMESTAMPTZ NOT NULL,
    -- consent_time + delay_seconds (default 30)
    initiated_at    TIMESTAMPTZ,
    connected_at    TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    
    -- Status
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    -- 'scheduled' | 'initiated' | 'ringing' | 'connected' | 'completed' | 
    -- 'no_answer' | 'busy' | 'failed' | 'cancelled'
    end_reason      VARCHAR(30),
    -- 'booked' | 'handoff' | 'lead_hangup' | 'no_answer' | 'error' | 'timeout'
    
    -- Call details
    duration_sec    INTEGER,
    recording_url   VARCHAR(500),
    transcript      TEXT,
    
    -- Context passed to voice agent
    dynamic_variables JSONB,
    -- { lead_name, service_type, price_range, yelp_project, ... }
    
    -- Transfer
    transferred_to  VARCHAR(20),
    -- Alex/tech phone if warm transfer
    transferred_at  TIMESTAMPTZ,
    
    -- Cost tracking
    cost_provider   DECIMAL(8,4),
    cost_telephony  DECIMAL(8,4),
    
    -- Retry
    attempt_number  INTEGER NOT NULL DEFAULT 1,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    parent_callback_id UUID REFERENCES ai_callbacks(id),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_callbacks_conversation ON ai_callbacks(conversation_id);
CREATE INDEX idx_ai_callbacks_status ON ai_callbacks(status) WHERE status IN ('scheduled', 'initiated');
CREATE INDEX idx_ai_callbacks_provider ON ai_callbacks(provider_call_id);
```

---

### `ai_channel_events`

Raw ingest events from external channels — audit trail and debugging.

```sql
CREATE TABLE ai_channel_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source
    channel         VARCHAR(30) NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
    -- 'yelp.new_lead' | 'yelp.new_message' | 'yelp.phone_available' |
    -- 'twilio.sms.inbound' | 'twilio.sms.status' | 'twilio.voice.status' |
    -- 'retell.call.started' | 'retell.call.ended' | 'retell.call.analyzed' |
    -- 'widget.message' | 'zapier.webhook'
    
    -- Processing
    processed       BOOLEAN NOT NULL DEFAULT false,
    processed_at    TIMESTAMPTZ,
    conversation_id UUID REFERENCES ai_conversations(id),
    error           TEXT,
    
    -- Raw payload
    payload         JSONB NOT NULL,
    headers         JSONB,
    
    -- Deduplication
    idempotency_key VARCHAR(255) UNIQUE,
    -- hash of channel + event_type + external_id
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_channel_events_unprocessed ON ai_channel_events(created_at) 
    WHERE processed = false;
CREATE INDEX idx_ai_channel_events_channel ON ai_channel_events(channel, event_type);
```

---

### `lead_channels`

Maps leads to their source channels — extends existing `leads.source`.

```sql
CREATE TABLE lead_channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID NOT NULL REFERENCES leads(id),
    contact_id      UUID NOT NULL REFERENCES contacts(id),
    
    channel         VARCHAR(30) NOT NULL,
    external_id     VARCHAR(255) NOT NULL,
    -- yelp_lead_id, thumbtack_request_id, etc.
    external_url    VARCHAR(500),
    
    -- Channel-specific
    project_data    JSONB,
    -- Yelp RAQ survey answers, Thumbtack job details
    
    is_primary      BOOLEAN NOT NULL DEFAULT true,
    -- first channel that created the lead
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(channel, external_id)
);

CREATE INDEX idx_lead_channels_lead ON lead_channels(lead_id);
CREATE INDEX idx_lead_channels_external ON lead_channels(channel, external_id);
```

---

### `kb_documents`

Knowledge base source documents.

```sql
CREATE TABLE kb_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    title           VARCHAR(255) NOT NULL,
    category        VARCHAR(30) NOT NULL,
    -- 'services' | 'zones' | 'faq' | 'hours' | 'policies'
    
    source_type     VARCHAR(20) NOT NULL,
    -- 'upload' | 'api' | 'manual' | 'csv_import'
    source_file     VARCHAR(500),
    -- S3/Railway file path for uploads
    
    content_raw     TEXT,
    -- original content before chunking
    
    is_active       BOOLEAN NOT NULL DEFAULT true,
    version         INTEGER NOT NULL DEFAULT 1,
    
    -- For services category
    service_id      VARCHAR(100),
    -- links to pricing catalog service_id
    
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_kb_documents_category ON kb_documents(category) WHERE is_active = true;
CREATE INDEX idx_kb_documents_service ON kb_documents(service_id) WHERE service_id IS NOT NULL;
```

---

### `kb_chunks`

Chunked + embedded KB content for RAG retrieval.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE kb_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    
    -- Embedding
    embedding       vector(1536),
    -- text-embedding-3-small
    
    -- Metadata for filtered retrieval
    category        VARCHAR(30) NOT NULL,
    service_id      VARCHAR(100),
    keywords        TEXT[],
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_kb_chunks_document ON kb_chunks(document_id);
CREATE INDEX idx_kb_chunks_embedding ON kb_chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_kb_chunks_category ON kb_chunks(category);
```

**Retrieval query example:**
```sql
SELECT content, category, service_id,
       1 - (embedding <=> $1::vector) AS similarity
FROM kb_chunks
WHERE category = ANY($2)
  AND 1 - (embedding <=> $1::vector) > 0.75
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

---

### `ai_bot_config`

Bot persona and behavior configuration — singleton per business (Phase 2: per organization).

```sql
CREATE TABLE ai_bot_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Persona
    bot_name        VARCHAR(100) NOT NULL DEFAULT 'Fast Glass Assistant',
    persona_prompt  TEXT NOT NULL,
    -- system prompt defining tone, rules, guardrails
    
    greeting_template TEXT,
    -- optional override; if NULL, AI generates from persona
    
    -- Behavior
    response_delay_ms INTEGER NOT NULL DEFAULT 2000,
    -- artificial delay so responses feel human (not instant)
    callback_delay_sec INTEGER NOT NULL DEFAULT 30,
    max_messages_before_handoff INTEGER NOT NULL DEFAULT 20,
    auto_escalate_keywords TEXT[] DEFAULT ARRAY['emergency', 'broken', 'shattered', 'injured'],
    
    -- Voice
    voice_provider  VARCHAR(20) DEFAULT 'retell',
    voice_agent_id  VARCHAR(255),
    -- Retell agent_id
    voice_id        VARCHAR(100) DEFAULT '11labs-Adrian',
    
    -- Hours
    business_hours  JSONB NOT NULL DEFAULT '{
        "mon": {"open": "08:00", "close": "18:00"},
        "tue": {"open": "08:00", "close": "18:00"},
        "wed": {"open": "08:00", "close": "18:00"},
        "thu": {"open": "08:00", "close": "18:00"},
        "fri": {"open": "08:00", "close": "18:00"},
        "sat": {"open": "09:00", "close": "15:00"},
        "sun": null
    }',
    after_hours_message TEXT DEFAULT 'Thanks for reaching out! We''re closed but I can still help with a quote or schedule a callback for tomorrow.',
    
    -- Model
    chat_model      VARCHAR(50) NOT NULL DEFAULT 'gpt-4.1',
    embedding_model VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
    
    -- Active
    is_active       BOOLEAN NOT NULL DEFAULT true,
    
    updated_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### `ai_analytics_daily`

Pre-aggregated daily metrics for dashboard.

```sql
CREATE TABLE ai_analytics_daily (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date            DATE NOT NULL,
    channel         VARCHAR(30),
    -- NULL = all channels
    
    -- Volume
    leads_received      INTEGER NOT NULL DEFAULT 0,
    conversations_started INTEGER NOT NULL DEFAULT 0,
    messages_inbound    INTEGER NOT NULL DEFAULT 0,
    messages_outbound   INTEGER NOT NULL DEFAULT 0,
    
    -- Speed
    avg_first_response_sec  DECIMAL(8,2),
    median_first_response_sec DECIMAL(8,2),
    pct_under_60s           DECIMAL(5,2),
    -- % of leads responded within 60 seconds
    
    -- Callbacks
    callbacks_requested INTEGER NOT NULL DEFAULT 0,
    callbacks_initiated INTEGER NOT NULL DEFAULT 0,
    callbacks_connected INTEGER NOT NULL DEFAULT 0,
    callbacks_booked    INTEGER NOT NULL DEFAULT 0,
    avg_callback_duration_sec DECIMAL(8,2),
    
    -- Conversion
    conversations_completed INTEGER NOT NULL DEFAULT 0,
    estimates_booked    INTEGER NOT NULL DEFAULT 0,
    handoffs_to_human   INTEGER NOT NULL DEFAULT 0,
    conversion_rate     DECIMAL(5,2),
    -- estimates_booked / conversations_started
    
    -- Cost
    cost_openai         DECIMAL(10,4) DEFAULT 0,
    cost_twilio_sms     DECIMAL(10,4) DEFAULT 0,
    cost_twilio_voice   DECIMAL(10,4) DEFAULT 0,
    cost_retell         DECIMAL(10,4) DEFAULT 0,
    cost_total          DECIMAL(10,4) DEFAULT 0,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(date, channel)
);

CREATE INDEX idx_ai_analytics_daily_date ON ai_analytics_daily(date DESC);
```

---

## Extensions to Existing Tables

### `contacts` — add columns

```sql
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
    ai_opt_out BOOLEAN DEFAULT false;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
    preferred_channel VARCHAR(30);
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS
    last_ai_contact_at TIMESTAMPTZ;
```

### `leads` — add columns

```sql
ALTER TABLE leads ADD COLUMN IF NOT EXISTS
    ai_conversation_id UUID REFERENCES ai_conversations(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS
    first_response_sec INTEGER;
    -- speed-to-lead metric
ALTER TABLE leads ADD COLUMN IF NOT EXISTS
    response_source VARCHAR(20);
    -- 'ai' | 'human' | 'none'
```

### `calls` — add columns

```sql
ALTER TABLE calls ADD COLUMN IF NOT EXISTS
    ai_callback_id UUID REFERENCES ai_callbacks(id);
ALTER TABLE calls ADD COLUMN IF NOT EXISTS
    call_type VARCHAR(20);
    -- 'inbound' | 'outbound_ai' | 'outbound_human' | 'warm_transfer'
```

---

## Seed Data

### Default bot config

```sql
INSERT INTO ai_bot_config (persona_prompt) VALUES (
'You are the AI assistant for Fast Glass & Windows, a trusted glass repair and replacement company serving the greater Los Angeles area.

RULES:
1. Be warm, professional, and concise. Use the lead''s first name.
2. NEVER quote exact prices without calling the get_price tool.
3. Always mention we can call them back in about 30 seconds for complex jobs.
4. If the lead mentions emergency (broken glass, injury), immediately call escalate_to_human.
5. Check service zone before quoting — we serve LA metro ZIP codes 90001-90899.
6. Business hours: Mon-Fri 8am-6pm, Sat 9am-3pm. After hours, offer callback scheduling.
7. Do not discuss competitors. Do not make promises about exact install dates.
8. If unsure, say "Let me connect you with our team" and escalate.'
);
```

### Service catalog import

```sql
-- Import from existing 51-service pricing data
INSERT INTO kb_documents (title, category, source_type, service_id, content_raw)
SELECT 
    name,
    'services',
    'csv_import',
    service_id,
    jsonb_pretty(row_to_json(s.*)::jsonb)
FROM services_catalog s;
-- services_catalog = temp import table from bot_correct.py pricing data
```

---

## Migration Order

1. `CREATE EXTENSION vector`
2. `ai_bot_config` (seed data)
3. `ai_conversations`
4. `ai_messages`
5. `ai_callbacks`
6. `ai_channel_events`
7. `lead_channels`
8. `kb_documents` + `kb_chunks`
9. `ai_analytics_daily`
10. ALTER existing tables (`contacts`, `leads`, `calls`)

---

## Estimated Storage (Year 1, 1,000 leads/mo)

| Table | Rows/year | Avg row size | Storage |
|-------|-----------|--------------|---------|
| ai_conversations | 12,000 | 1 KB | 12 MB |
| ai_messages | 120,000 | 500 B | 60 MB |
| ai_callbacks | 5,000 | 2 KB | 10 MB |
| ai_channel_events | 50,000 | 3 KB | 150 MB |
| kb_chunks | 200 | 8 KB (w/ embedding) | 1.6 MB |
| ai_analytics_daily | 365 | 500 B | 0.2 MB |
| **Total** | | | **~234 MB** |

Negligible compared to existing ROMI CRM data.
