# BUILD BRIEF — AI Lead Responder Backend Skeleton (Phase 0→1 bridge)

> **Assigned by:** Senya (Tech Lead) for Alex
> **Date:** 2026-06-14
> **Type:** PRODUCTION CODE — build the backend skeleton
> **Path chosen by Alex:** B (GHL stopgap now + build own backend in parallel)

---

## GOAL

Build the ROMI backend skeleton for the AI Lead Responder so we can switch
Zapier from GHL → our own OpenAI brain within ~1 week.

This is the FOUNDATION. Text-first (Phase 0/1), voice-ready (Phase 1 hooks
present but not implemented yet).

Follow the approved design in `docs/ai-responder/DESIGN.md` and
`docs/ai-responder/DATA_MODEL.md`. Do NOT deviate from that architecture.

---

## SCOPE (what to build NOW)

### 1. FastAPI app skeleton
- `backend/` structure (if not exists): app, routers, models, services, config
- Health endpoint `GET /health`
- Settings via env vars (no hardcoded secrets)

### 2. Ingest webhook (the critical piece)
- `POST /api/v1/ai-responder/webhooks/zapier/yelp`
  - Receives a Yelp lead from Zapier (name, service, location, message, phone)
  - Normalizes into unified lead format
  - Stores in DB
  - Triggers AI brain to generate first response
  - Returns the AI reply text (so Zapier can post it back to Yelp)

### 3. AI Brain (text, Phase 0/1)
- `services/ai_brain.py`
  - OpenAI call (GPT-4o or GPT-4.1) with Fast Glass system prompt
  - State machine: GREET → QUALIFY → OFFER → CALLBACK/CLOSE → HANDOFF
  - Knowledge base injection (start simple: hardcoded Fast Glass facts +
    51-service price ranges as a JSON file `data/fast_glass_kb.json`)
  - Tool stubs (define signatures, implement get_price + book_estimate;
    leave trigger_callback as a STUB that just logs — voice comes Phase 1)

### 4. Database (from DATA_MODEL.md)
- Implement the core tables needed for text flow:
  `ai_conversations`, `ai_messages`, `lead_channels`, `kb_documents`
- Use SQLAlchemy + Alembic migration
- Leave voice tables (`ai_callbacks`) as migration-ready but unused

### 5. SMS webhook stub (Phase 1 prep)
- `POST /api/v1/ai-responder/webhooks/twilio/sms` — accept + store, reply via brain

---

## OUT OF SCOPE (do NOT build yet)
- ❌ Voice / Retell integration (Phase 1 — only leave hook stubs)
- ❌ Admin UI / Next.js frontend (Phase 2)
- ❌ RAG vector DB (start with simple JSON KB; vector later)
- ❌ Real Yelp API (we use Zapier as the bridge)

---

## CONSTRAINTS
- Production-grade: typed, tested, no hardcoded secrets, env config
- Follow DESIGN.md architecture exactly (3 layers: Ingest → Brain → Action)
- Reuse ROMI stack: FastAPI, PostgreSQL, SQLAlchemy, OpenAI
- Add `backend/README.md` with run instructions + env vars list
- Add basic tests for the webhook + ai_brain (pytest)
- Work in a feature branch, open a PR (do not push to main directly)

## DELIVERABLES
- Working `POST /webhooks/zapier/yelp` that takes a lead and returns an AI reply
- `data/fast_glass_kb.json` knowledge base (51 services price ranges + facts)
- Alembic migration for core tables
- `backend/README.md`
- Tests passing
- PR with summary + how to deploy on Railway

## FAST GLASS CONTEXT (for the AI prompt + KB)
- Company: Fast Glass & Windows, Los Angeles glass/window repair
- Services: window glass replacement, storefront, shower doors, auto glass,
  emergency board-up, window tint, mirrors (51 services total)
- Service area: 100-mile radius from 1730 Westwood Blvd, LA 90024
- Hours: Mon-Fri 8am-6pm, Sat 9am-4pm; 24/7 emergency
- Phones: 213-772-6882 (Yelp/general), 213-566-8886 (main/emergency)
- Tone: friendly, fast, confident, local. Goal: respond <60s, qualify, close
  to estimate booking or callback. Keep replies short (Yelp chat).
- Rating: 4.5 stars, 22 reviews on Yelp

When done: commit, push to feature branch, open PR, write summary.
