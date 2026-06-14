# AI Lead Responder — Design Complete ✅

> **Module:** ROMI CRM Module 10 — AI Agent (24/7 voice + SMS)  
> **Completed:** 2026-06-14  
> **Branch:** `cursor/ai-lead-responder-design-68b2`  
> **Type:** Research + Design only — no production code

---

## Summary

Complete design package for the AI Lead Responder platform — an AI Sales Development Rep (SDR) that captures leads from any channel, responds instantly with real AI (not templates), qualifies leads with 51-service pricing knowledge, and closes to action via SMS or 30-second voice callback.

---

## Deliverables

| File | Description | Status |
|------|-------------|--------|
| [RESEARCH.md](./RESEARCH.md) | Competitor analysis: Hatch, Podium, Vapi, Retell, Bland, GHL, Voiceflow, OpenAI Realtime | ✅ |
| [DESIGN.md](./DESIGN.md) | 3-layer architecture, state machine, RAG, tool calling, voice callback, channel integrations | ✅ |
| [BUILD_VS_BUY.md](./BUILD_VS_BUY.md) | Phased recommendation (Phase 0–3) with cost projections | ✅ |
| [DATA_MODEL.md](./DATA_MODEL.md) | PostgreSQL schema: 8 new tables + extensions to existing | ✅ |
| [UI_MOCKUP.md](./UI_MOCKUP.md) | Admin dashboard: 8 screens with ASCII wireframes | ✅ |

---

## Key Decisions

### 1. Voice Provider: Retell AI (not Vapi)
- **~$0.09–0.11/min** all-in with BYO Twilio (Fast Glass already has Twilio)
- Outbound API: `POST /v2/create-phone-call` with dynamic variables
- Built-in KB, warm transfer, 2–4 hour setup for 1 dev
- Vapi deferred — better for Phase 3 SaaS with granular provider control

### 2. Phased Rollout
| Phase | What | When | Cost |
|-------|------|------|------|
| **0** | Zapier + GHL text autoresponse | Week 1–2 | ~$10/mo |
| **1** | + Retell voice callback | Week 3–6 | ~$123/mo |
| **2** | Full ROMI backend | Month 2–4 | ~$336/mo |
| **3** | SaaS for other glass companies | Month 6+ | Revenue-positive |

### 3. Rejected: Hatch, Podium
- $400–2,000+/mo with annual contracts
- CRM lock-in — ROMI is the product, not a parallel platform

### 4. Yelp Integration: Zapier (until partner API)
- Fast Glass has RAQ enabled; Zapier is official bridge
- Unlimited tasks for Yelp advertisers
- July 7 meeting with Jess Greenbaum may unlock direct API

---

## Architecture at a Glance

```
Channels (Yelp/SMS/Web) → INGEST → AI BRAIN (OpenAI + RAG) → ACTION (Twilio SMS / Retell Voice / ROMI CRM)
```

**State machine:** greet → qualify → offer → close / callback → voice_active → complete / handoff

**Tools:** `get_price`, `check_availability`, `book_estimate`, `trigger_callback`, `escalate_to_human`

---

## Speed-to-Lead Target

| Metric | Target | Rationale |
|--------|--------|-----------|
| First response | < 60 seconds | Velocify: +391% conversion within 1 min |
| Callback initiation | < 45 seconds after consent | "Call you in 30 seconds" promise |
| Under-60s rate | > 90% | Currently 13+ hour waits on some leads |

---

## Database Additions

8 new tables: `ai_conversations`, `ai_messages`, `ai_callbacks`, `ai_channel_events`, `lead_channels`, `kb_documents`, `kb_chunks`, `ai_bot_config`, `ai_analytics_daily`

Extends existing: `contacts`, `leads`, `calls`

Estimated storage: ~234 MB/year at 1,000 leads/month.

---

## Admin UI

8 screens under `/dashboard/ai-responder/`:
1. Unified Lead Inbox (all channels)
2. Conversation Detail (thread + takeover)
3. Live Monitor (real-time activity feed)
4. Analytics (speed-to-lead hero KPI + funnel)
5. Settings: Persona
6. Settings: Knowledge Base
7. Settings: Channels
8. Settings: Voice Agent

---

## Next Steps (for Senya / Alex)

### This week (Phase 0)
1. Alex: Configure GHL Conversation AI with Fast Glass FAQ
2. Senya: Zapier Zap — Yelp New Lead → GHL
3. Alex: Test with real Yelp RAQ; measure response time

### Week 3 (Phase 1)
4. Senya: Retell account + Fast Glass SDR agent
5. Senya: ROMI webhook endpoint for Zapier redirect
6. Alex: Review 10 AI voice calls

### July 7
7. Alex: Yelp partner meeting — direct Leads API access

### Month 2 (Phase 2)
8. Senya: Implement schema from DATA_MODEL.md
9. Senya: Build admin UI from UI_MOCKUP.md
10. Alex: Deprecate GHL for lead response

---

## Constraints Honored

- ✅ No production backend/frontend code written
- ✅ No changes to `backend/*` or `frontend/*`
- ✅ All work inside `docs/ai-responder/` only
- ✅ Reuses ROMI stack: FastAPI, PostgreSQL, Twilio, OpenAI
- ✅ Concrete: real API names, pricing, sequence diagrams
- ✅ Production-grade thinking throughout

---

## References

- Design brief: [docs/AI_LEAD_RESPONDER_DESIGN_BRIEF.md](../AI_LEAD_RESPONDER_DESIGN_BRIEF.md)
- ROMI architecture: [docs/ARCHITECTURE.md](../ARCHITECTURE.md)
- Agent roles: [docs/AGENTS.md](../AGENTS.md)
