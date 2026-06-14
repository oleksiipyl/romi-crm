# ROMI CRM — Backend (AI Lead Responder)

FastAPI backend skeleton for **Module 10: AI Lead Responder**. Text-first ingest via Zapier (Yelp) and Twilio SMS stub; voice-ready hooks (Retell stub logs only).

## Quick Start

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DATABASE_URL and OPENAI_API_KEY
```

### Database migration

```bash
# PostgreSQL (production / Railway)
alembic upgrade head
```

### Run dev server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`

## API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health |
| `POST` | `/api/v1/ai-responder/webhooks/zapier/yelp` | Yelp lead via Zapier → AI reply |
| `POST` | `/api/v1/ai-responder/webhooks/twilio/sms` | Inbound SMS stub → AI reply |

### Zapier Yelp webhook

**URL:** `POST /api/v1/ai-responder/webhooks/zapier/yelp`

**Headers (optional):** `X-Webhook-Secret: <ZAPIER_WEBHOOK_SECRET>`

**Sample payload (New Lead):**
```json
{
  "trigger": "new_lead",
  "lead_id": "yelp_abc123",
  "consumer_name": "Victor M.",
  "phone_number": "+13105551234",
  "project_description": "Sliding patio door glass replacement",
  "zip_code": "90034",
  "service_type": "Door Installation"
}
```

**Response:**
```json
{
  "status": "ok",
  "conversation_id": "uuid",
  "reply_text": "Hi Victor! Thanks for reaching out...",
  "state": "greet",
  "event_type": "new_lead",
  "fallback": false,
  "tools_called": []
}
```

Use `reply_text` in Zapier's **Create Message** action to post back to Yelp.

**Zapier setup:**
1. Trigger: Yelp Leads → New Lead (or New Consumer Message)
2. Action: Webhooks by Zapier → POST to ROMI URL
3. Action: Yelp Leads → Create Message (use `reply_text` from step 2)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key (*fallback replies if empty) |
| `OPENAI_MODEL` | No | `gpt-4o` | Chat model for AI brain |
| `ZAPIER_WEBHOOK_SECRET` | No | — | If set, requires `X-Webhook-Secret` header |
| `KB_PATH` | No | `data/fast_glass_kb.json` | Knowledge base JSON path |
| `APP_ENV` | No | `development` | Environment name |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (env vars)
│   ├── api/
│   │   ├── health.py
│   │   └── v1/ai_responder.py   # Webhook routes
│   ├── models/ai_responder.py   # SQLAlchemy models
│   ├── schemas/ai_responder.py  # Pydantic schemas
│   ├── services/
│   │   ├── ai_brain.py      # OpenAI + state machine
│   │   ├── ingest.py        # Zapier normalizer
│   │   ├── kb.py            # JSON knowledge base
│   │   ├── tools.py         # get_price, book_estimate, stubs
│   │   └── state_machine.py
│   └── db/                  # SQLAlchemy session
├── alembic/                 # Migrations
├── data/fast_glass_kb.json  # 51 services + company facts
├── tests/                   # pytest
└── requirements.txt
```

## Tests

```bash
cd backend
pytest -v
```

Tests use in-memory SQLite (no PostgreSQL required).

## Architecture

Follows `docs/ai-responder/DESIGN.md` 3-layer model:

1. **Ingest** — `ingest.py` normalizes Zapier/Twilio payloads
2. **AI Brain** — `ai_brain.py` OpenAI GPT-4o + state machine + tools
3. **Action** — returns `reply_text` (Zapier posts to Yelp); voice stub logs only

## Voice (Phase 1 — not implemented)

`trigger_callback` in `services/tools.py` logs intent only. Retell integration comes in Phase 1 voice sprint.

## Notes

- `contact_id` / `lead_id` are UUIDs without FK to core CRM tables (pending core schema migration).
- KB is JSON file, not vector RAG (Phase 2).
- Price ranges in `fast_glass_kb.json` are **placeholders** — Alex will correct.
