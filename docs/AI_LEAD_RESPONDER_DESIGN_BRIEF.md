# AI Lead Responder — Design Brief (Module 10 of ROMI CRM)

> **Assigned by:** Senya (OpenClaw Tech Lead) for Alex (American Glazier)
> **Date:** 2026-06-14
> **Type:** RESEARCH + DESIGN ONLY — do NOT write production code yet
> **Module:** This is Module 10 "AI Agent (24/7 voice + SMS)" of ROMI CRM

---

## CONTEXT

Fast Glass & Windows (LA glass repair company) gets leads from Yelp, Thumbtack,
Google, website. Currently answers manually → loses hot leads (some wait 13+ hours).

Alex's vision: an **AI Lead Responder Platform** — an AI Sales Development Rep (SDR)
that:
1. Captures leads from ANY channel (Yelp, website, Thumbtack, Google, phone)
2. Instantly responds with context (not templates — real AI with knowledge base)
3. Holds a conversation, qualifies the lead, knows pricing (51 services), service zones
4. Closes to action: callback / book estimate / phone call
5. Can INITIATE a two-way phone call ("Victor, we got your door request —
   want us to call you back in 30 seconds?")

This is part of ROMI CRM (Module 10). Build it inside this repo.

---

## YOUR TASK (Design Agent — Agent #1)

### Phase 1: RESEARCH best-in-class apps
Study how the market leaders do AI lead response + voice callback:
- **Hatch** (usehatchapp.com) — AI lead engagement for home services
- **Podium** — messaging + AI for local business
- **Vapi** (vapi.ai) — voice AI infrastructure
- **Retell AI** (retellai.com) — voice AI agents
- **Bland AI** — voice AI
- **GoHighLevel** — conversation AI + workflows
- **Voiceflow** — conversational design
- **OpenAI Realtime API** — voice

For each, document:
- Core UX patterns (how the admin configures the bot)
- How they handle voice callback / speed-to-lead
- Knowledge base / context injection approach
- Pricing model
- What's good to copy, what to avoid

### Phase 2: DESIGN our platform
Produce a complete design document covering:

1. **System architecture** (3 layers: Ingest → AI Brain → Action)
   - Fit into existing ROMI CRM architecture (see docs/ARCHITECTURE.md)
   - Reuse: FastAPI backend, PostgreSQL, Twilio, OpenAI (already in stack)

2. **Conversation flow design**
   - State machine: greet → qualify → offer → close → callback/handoff
   - Knowledge base structure (RAG): 51 services, prices, zones, hours, FAQ
   - Tool-calling design: get_price, check_availability, book_estimate,
     trigger_callback, escalate_to_human

3. **Voice callback flow** (the killer feature)
   - "Want a callback in 30 seconds?" → consent → Twilio outbound call
   - Option A: Voice AI speaks (Vapi/Retell) — recommend which one + why
   - Option B: Bridge to live human (Alex/tech)
   - Sequence diagram

4. **Admin UI/UX** (Next.js dashboard mockup, described or wireframe)
   - Configure bot persona, knowledge base, response templates
   - Live conversation monitor
   - Lead inbox (all channels unified)
   - Analytics: response time, conversion, callback success

5. **Channel integrations design**
   - Yelp (via Zapier initially — Yelp Leads API is Partner-only)
   - Website widget
   - SMS (Twilio)
   - Future: Thumbtack, Google LSA

6. **Data model** (new tables for ROMI CRM PostgreSQL)
   - conversations, messages, lead_channels, callbacks, kb_documents

### Phase 3: RECOMMENDATION — Build vs Buy
Honest analysis with a clear recommendation, phased:
- Phase 0: Zapier + ChatGPT + GHL (text autoresponse) — fastest validation
- Phase 1: + Vapi/Retell + Twilio voice callback
- Phase 2: Own backend (this repo) — full platform
- Phase 3: SaaS product for other glass/home-services companies

---

## DELIVERABLES (commit to this repo)

Create these files under `docs/ai-responder/`:
- `RESEARCH.md` — competitor analysis (Phase 1)
- `DESIGN.md` — full system + conversation + voice design (Phase 2)
- `BUILD_VS_BUY.md` — recommendation with phases (Phase 3)
- `DATA_MODEL.md` — PostgreSQL schema additions
- `UI_MOCKUP.md` — admin dashboard UX (described/wireframe)

## CONSTRAINTS
- DO NOT write production backend/frontend code yet — design only
- DO NOT touch existing `backend/*` or `frontend/*` if present
- Work only inside `docs/ai-responder/`
- Reuse existing ROMI CRM stack (don't invent new tech without justification)
- Be concrete: real pricing, real API names, real sequence diagrams
- Production-grade thinking, no hand-waving

## KNOWN FACTS (use these)
- Yelp Leads API = Partner-only (needs advertising reseller status)
- Yelp Leads API does NOT support "Message the Business", only RAQ
- Fast Glass HAS RAQ enabled (confirmed)
- Zapier is the official no-code bridge for Yelp Leads
- Fast Glass has: OpenAI key, Railway, GHL (12 numbers), HCP, 51-service pricing
- Speed-to-lead: response <1 min = +391% conversion (cite real studies)
- Meeting with Jess Greenbaum (Yelp partner) July 7 — may unlock direct API

When done, commit + push, and create `docs/ai-responder/DONE.md` with a summary.

---

## ADDENDUM (2026-06-14 09:56) — уточнения от Alex

### КЛЮЧЕВОЕ: цель = СВОЯ CRM (не GHL-зависимость)
- GHL временный ("temp" в стеке). Voice НЕ должен жить внутри GHL.
- Voice-движок подключается НАПРЯМУЮ к нашему ROMI CRM backend через API.
- ОТКЛОНИТЬ GHL-native решения (Thinkrr native-to-GHL) для core платформы.

### Voice stack — API-first (не привязанный к чужой CRM)
Рекомендовать standalone voice-стек:
- **Orchestration:** Vapi vs Retell (сравнить call-transfer / latency / tool-calls)
- **Brain:** GPT-4o / Claude (tool-calling: get_price, book_estimate, check_availability)
- **TTS voice:** ElevenLabs или аналог (естественный голос)
- **Telephony:** Twilio
Цель: тот же или ЛУЧШИЙ "ум" чем у Thinkrr, но напрямую в нашей CRM.

### Benchmark качества = Thinkrr.ai
- Alex тестил Thinkrr 1.5 года назад — впечатлил "ум модели"
- Thinkrr вероятно использует чужой движок (Vapi/Retell + ElevenLabs + LLM) + свой UI + GHL-native
- ЗАДАЧА: выяснить какой движок под капотом Thinkrr, и собрать ТО ЖЕ качество напрямую
- Thinkrr = эталон UX/качества для бенчмарка, НЕ инструмент для нас

### Гибрид-логика звонка (решение Alex) — заложить в дизайн
1. Лид пишет → "перезвоним за 30 сек?"
2. Клиент ОК → звоним ЖИВОМУ первым (Alex/техник)
3. Живой не берёт быстро (~5-8 сек) → перехватывает AI-голос
4. Гарантия: клиент получает разговор за 30 сек (человек ИЛИ AI)
→ Спроектировать call-routing с no-answer fallback на AI.

### ФАЗЫ — "правильно + не забыть"
- ПРОЕКТИРОВАТЬ всю систему СРАЗУ (текст + voice единым дизайном)
- Архитектура с 1-го дня имеет "дырку" под voice-callback (даже если код позже)
- Реализация: Фаза 0 = текст-автоответ Yelp, Фаза 1 = voice-callback
- Voice НЕ "прикручиваем потом" — заложен в фундамент data-model и API с начала
- В DATA_MODEL.md и DESIGN.md сразу предусмотреть таблицы/эндпоинты для callbacks,
  даже если реализуются в Фазе 1
