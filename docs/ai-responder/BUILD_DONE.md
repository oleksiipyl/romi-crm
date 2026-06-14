# AI Lead Responder — Backend Phase 1 Build Complete ✅

> **Branch:** `cursor/ai-responder-backend-phase1-68b2`  
> **Completed:** 2026-06-14  
> **Type:** Production code — FastAPI backend skeleton

---

## Summary

Built the ROMI CRM **AI Lead Responder backend skeleton** so Zapier can switch from GHL to our own OpenAI brain within ~1 week. Text-first ingest is live; voice hooks are stub-only (Retell deferred).

---

## What Was Built

| Component | Path | Status |
|-----------|------|--------|
| FastAPI app + `/health` | `backend/app/main.py` | ✅ |
| Zapier Yelp webhook | `POST /api/v1/ai-responder/webhooks/zapier/yelp` | ✅ |
| Twilio SMS stub | `POST /api/v1/ai-responder/webhooks/twilio/sms` | ✅ |
| AI Brain (GPT-4o) | `backend/app/services/ai_brain.py` | ✅ |
| State machine | GREET → QUALIFY → OFFER → CALLBACK/CLOSE → HANDOFF | ✅ |
| Knowledge base | `backend/data/fast_glass_kb.json` (51 services) | ✅ |
| Tools | `get_price`, `book_estimate` implemented; `trigger_callback` logs stub | ✅ |
| DB models + migration | `ai_conversations`, `ai_messages`, `lead_channels`, `kb_documents` | ✅ |
| Tests | 13 pytest tests (webhook + brain + tools) | ✅ All passing |
| Run docs | `backend/README.md` | ✅ |

---

## Architecture (3 Layers)

```
Zapier/Twilio → INGEST (ingest.py) → AI BRAIN (ai_brain.py + tools.py) → reply_text
```

Zapier uses `reply_text` from the webhook response in **Yelp Leads → Create Message**.

---

## Quick Test

```bash
cd backend
pip install -r requirements.txt
python3 -m pytest -v
uvicorn app.main:app --reload --port 8000

curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/v1/ai-responder/webhooks/zapier/yelp \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "new_lead",
    "lead_id": "test_001",
    "consumer_name": "Victor M.",
    "phone_number": "+13105551234",
    "project_description": "Sliding patio door glass replacement",
    "zip_code": "90034"
  }'
```

---

## Railway Deploy Steps

### 1. Create Railway project
- Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
- Select `oleksiipyl/romi-crm` repo, branch `cursor/ai-responder-backend-phase1-68b2` (or `main` after merge)
- Set **Root Directory** to `backend`

### 2. Add PostgreSQL
- Railway dashboard → **+ New** → **Database** → **PostgreSQL**
- Copy `DATABASE_URL` from PostgreSQL service variables

### 3. Set environment variables

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway reference) |
| `OPENAI_API_KEY` | Your OpenAI key |
| `OPENAI_MODEL` | `gpt-4o` |
| `ZAPIER_WEBHOOK_SECRET` | Random secret (optional, recommended) |
| `KB_PATH` | `data/fast_glass_kb.json` |
| `APP_ENV` | `production` |

### 4. Configure start command

Railway **Settings → Deploy → Start Command:**
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or add a `Procfile` / `railway.toml` (optional future improvement).

### 5. Run migration
Migration runs automatically if start command includes `alembic upgrade head`.

Manual:
```bash
railway run alembic upgrade head
```

### 6. Get public URL
- Railway → Settings → Networking → **Generate Domain**
- Webhook URL: `https://<your-domain>.up.railway.app/api/v1/ai-responder/webhooks/zapier/yelp`

### 7. Update Zapier
1. **Webhooks by Zapier → POST** to Railway URL above
2. Header: `X-Webhook-Secret: <your secret>` (if configured)
3. Map Yelp fields: `lead_id`, `consumer_name`, `project_description`, `zip_code`, `phone_number`
4. **Yelp Leads → Create Message** using `reply_text` from webhook response

### 8. Verify
```bash
curl https://<your-domain>.up.railway.app/health
```

---

## Out of Scope (as planned)

- ❌ Retell / voice integration (`trigger_callback` logs only)
- ❌ Admin UI / Next.js frontend
- ❌ pgvector RAG (JSON KB only)
- ❌ Direct Yelp Leads API

---

## Next Steps (Senya / Alex)

1. **Alex:** Review placeholder prices in `backend/data/fast_glass_kb.json`
2. **Senya:** Deploy to Railway, set env vars, run migration
3. **Alex:** Redirect Zapier from GHL → ROMI webhook URL
4. **Measure:** Speed-to-lead < 60s for 90%+ Yelp leads
5. **Phase 1 voice:** Implement Retell in `trigger_callback` (see `docs/ai-responder/DESIGN.md`)

---

## Files Changed

```
backend/
├── app/                    # FastAPI application
├── alembic/                # DB migrations
├── data/fast_glass_kb.json # 51-service KB
├── tests/                  # 13 pytest tests
├── requirements.txt
├── README.md
└── .env.example
docs/ai-responder/BUILD_DONE.md
```

---

## References

- Build brief: `docs/ai-responder/BUILD_PHASE1_BRIEF.md`
- Design: `docs/ai-responder/DESIGN.md`
- Data model: `docs/ai-responder/DATA_MODEL.md`
