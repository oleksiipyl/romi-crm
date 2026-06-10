# ROMI CRM — System Architecture

## Tech Stack

```
┌─────────────────────────────────────────────────┐
│                   CLIENTS                        │
│  Web Browser    iOS App    Android App           │
└────────┬───────────┬──────────┬──────────────────┘
         │           │          │
         ▼           ▼          ▼
┌─────────────────────────────────────────────────┐
│              NEXT.JS FRONTEND                    │
│         (Vercel or Mac Mini)                     │
│  Dashboard | Pipeline | Quotes | Reports         │
└────────────────────┬────────────────────────────┘
                     │ REST API
                     ▼
┌─────────────────────────────────────────────────┐
│              FASTAPI BACKEND                     │
│         (Mac Mini / VPS)                         │
│  Auth | Leads | Jobs | Pricing | Reports         │
└──┬──────────────────┬─────────────────┬──────────┘
   │                  │                 │
   ▼                  ▼                 ▼
┌──────────┐   ┌────────────┐   ┌─────────────────┐
│PostgreSQL│   │   Redis    │   │   File Storage  │
│(main DB) │   │(cache/jobs)│   │ (photos, PDFs)  │
└──────────┘   └────────────┘   └─────────────────┘

EXTERNAL INTEGRATIONS:
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐
│  Twilio  │  │CallRail  │  │ OpenAI   │  │ GHL  │
│ Voice+SMS│  │Tracking  │  │GPT+Whispr│  │(temp)│
└──────────┘  └──────────┘  └──────────┘  └──────┘
```

## Database Schema (Core Tables)

```sql
-- Users (team members)
users: id, email, password_hash, name, role, phone, created_at

-- Contacts (customers)
contacts: id, first_name, last_name, phone, email, address, 
          zip_code, source, created_at, assigned_to

-- Leads (inbound requests)
leads: id, contact_id, stage, source, source_detail,
       call_id, tracking_number, created_at, updated_at

-- Pipeline Stages
stages: Lead → Measure Scheduled → Measure Done → 
        Quote Sent → Contract → In Progress → Paid → Closed

-- Jobs (work orders)
jobs: id, lead_id, technician_id, scheduled_at, address,
      glass_type, dimensions_w, dimensions_h, 
      material_cost, labor_cost, total_price,
      status, notes

-- Quotes
quotes: id, job_id, items_json, total, pdf_url, 
        sent_at, accepted_at

-- Calls
calls: id, contact_id, direction, duration, recording_url,
       transcript, from_number, to_number, 
       tracking_number, source, created_at

-- Claims
claims: id, job_id, type, description, photos_json,
        status, resolution, created_at
```

## API Structure

```
/api/v1/
  auth/
    POST /login
    POST /refresh
    POST /logout
  
  contacts/
    GET    /           (list with filters)
    POST   /           (create)
    GET    /:id        (detail)
    PUT    /:id        (update)
    DELETE /:id        (soft delete)
  
  leads/
    GET    /           (pipeline view)
    POST   /           (create from call/form)
    PUT    /:id/stage  (move pipeline stage)
  
  jobs/
    GET    /
    POST   /
    GET    /:id
    PUT    /:id
    POST   /:id/quote  (generate quote)
  
  pricing/
    POST   /calculate  (dimensions + glass type → price)
  
  calls/
    POST   /webhook/twilio    (inbound call)
    POST   /webhook/callrail  (call tracking data)
  
  reports/
    GET    /dashboard   (KPIs)
    GET    /revenue     (date range)
    GET    /sources     (attribution)
    GET    /team        (performance)
```

## Environment Variables Required

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/romi_crm

# Auth
JWT_SECRET=<random 32 bytes>
JWT_EXPIRE_HOURS=24

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxx
TWILIO_AUTH_TOKEN=xxxxxx
TWILIO_FROM_NUMBER=+12135668886

# OpenAI
OPENAI_API_KEY=sk-xxxxxx

# CallRail
CALLRAIL_API_KEY=xxxxxx

# App
APP_URL=https://crm.fastglass.com
FRONTEND_URL=https://app.fastglass.com
```
