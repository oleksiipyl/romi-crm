# AI Lead Responder — Build vs Buy Recommendation (Phase 3)

> **Module:** ROMI CRM Module 10  
> **Date:** 2026-06-14  
> **Decision owner:** Alex (Product) + Senya (Tech Lead)

---

## Executive Recommendation

**Do not buy Hatch or Podium.** They solve the right problem but at $400–2,000+/mo with annual contracts and CRM lock-in. Fast Glass already has the building blocks (Twilio, OpenAI, GHL, ROMI CRM repo).

**Phased approach:**

| Phase | Timeline | Stack | Monthly Cost (est.) |
|-------|----------|-------|---------------------|
| **Phase 0** | Week 1–2 | Zapier + GHL Conversation AI | $0–50 incremental |
| **Phase 1** | Week 3–6 | + Retell voice callback | $50–200 |
| **Phase 2** | Month 2–4 | ROMI backend (this repo) | $100–400 |
| **Phase 3** | Month 6+ | SaaS for other glass companies | Revenue-positive |

**Total Year 1 estimated spend:** $3,000–8,000 (vs $5,000–15,000 for Hatch/Podium).

---

## Buy Options Considered

### Option A: Hatch (Full Platform)

| Pros | Cons |
|------|------|
| Home-services proven (2,000+ customers) | No public pricing — sales-led, annual contract |
| Voice + SMS + email unified | Does not integrate with ROMI CRM natively |
| White-glove AI setup | Mid-market pricing ($500–2,000+/mo estimated) |
| Yelp/Angi/ServiceTitan integrations | Replaces ROMI instead of extending it |

**Verdict:** ❌ **Reject.** Wrong strategic fit — Alex is building ROMI as the CRM, not buying a parallel platform.

### Option B: Podium (Messaging + AI Concierge)

| Pros | Cons |
|------|------|
| Strong unified inbox UX | $399–599/mo minimum |
| AI Concierge for text qualification | No voice callback AI |
| Review management (bonus) | 12-month contracts |
| 200+ integrations | Review features irrelevant to glass repair |

**Verdict:** ❌ **Reject.** Paying for review management we don't need; no voice callback.

### Option C: GoHighLevel Only (Extend Current)

| Pros | Cons |
|------|------|
| Already have 12 numbers + account | Not our CRM — ROMI is the product |
| Conversation AI at $0.02/msg | Voice AI outbound is pay-per-use ($0.16+/min) |
| Zapier-like workflows built in | $97/mo per sub-account for unlimited AI |
| Fastest Phase 0 setup | Data siloed from ROMI PostgreSQL |

**Verdict:** ✅ **Phase 0 bridge only.** Use for 2–4 weeks while ROMI Module 10 ingest layer is built.

### Option D: Retell + ROMI (Recommended)

| Pros | Cons |
|------|------|
| Best voice callback cost (~$0.09–0.11/min BYO Twilio) | Requires ROMI backend for orchestration |
| Outbound API with dynamic variables | Retell is a dependency (mitigated: BYO everything else) |
| Built-in KB for voice context | 1 dev to integrate (Senya) |
| Warm transfer to Alex | — |
| Data in ROMI PostgreSQL | — |

**Verdict:** ✅ **Phase 1 voice layer.** Best cost/capability for 1-person tech team.

### Option E: Build Everything (OpenAI Realtime + Custom)

| Pros | Cons |
|------|------|
| Full control, no vendor lock-in | 4–8 weeks engineering for voice bridge |
| Lowest marginal cost at scale | Twilio Media Streams ↔ Realtime WebSocket is complex |
| Phase 3 SaaS ready | ~$0.25/min not cheaper than Retell at low volume |
| Same OpenAI key already in stack | No time for this in Phase 0/1 |

**Verdict:** ⏳ **Phase 2+ only.** Build text brain first; voice bridge after product-market fit.

---

## Phased Implementation Plan

### Phase 0: Zapier + GHL (Text Autoresponse) — Weeks 1–2

**Goal:** Respond to Yelp RAQ leads in < 60 seconds via SMS/text while ROMI is being built.

**Architecture:**
```
Yelp RAQ → Zapier (New Lead trigger) → GHL (create contact + start Conversation AI)
                                     → Slack notification to Alex
         → Zapier (Phone Availability) → GHL (update contact phone)
```

**Setup checklist:**
- [ ] Zap 1: Yelp New Lead → GHL Create Contact + Send Conversation AI reply
- [ ] Zap 2: Yelp Phone Availability → GHL Update Phone
- [ ] Zap 3: Yelp New Consumer Message → GHL Continue Conversation AI
- [ ] GHL Conversation AI: upload 51-service FAQ + pricing ranges
- [ ] GHL workflow: if "call me" detected → SMS Alex with lead details
- [ ] Measure: log response times in GHL for 2 weeks

**Cost:**

| Item | Cost |
|------|------|
| Zapier (Yelp advertiser) | $0 (unlimited tasks for Yelp Leads) |
| GHL (existing) | $0 incremental (already paying) |
| Conversation AI | $0.02/msg × ~500 msgs = **$10/mo** |
| **Total Phase 0** | **~$10/mo** |

**Success criteria:**
- 90%+ leads get first reply within 60 seconds
- Baseline conversion rate measured (before/after)
- Alex confirms AI responses are accurate enough

**Exit criteria → Phase 1:**
- 2 weeks of data showing improved response time
- Senya has ROMI webhook endpoint ready for Zapier redirect

---

### Phase 1: + Retell Voice Callback — Weeks 3–6

**Goal:** "Want us to call you back in 30 seconds?" — AI voice calls the lead.

**Architecture:**
```
Yelp → Zapier → ROMI webhook (ingest)
              → OpenAI brain (SMS via Twilio)
              → On consent: Retell POST /v2/create-phone-call (30s delay)
              → Retell webhooks → ROMI (update conversation)
```

**Setup checklist:**
- [ ] ROMI: `POST /api/v1/ai-responder/webhooks/zapier/yelp`
- [ ] ROMI: `POST /api/v1/ai-responder/webhooks/twilio/sms`
- [ ] ROMI: AI brain with state machine (GREET → QUALIFY → OFFER → CALLBACK)
- [ ] Retell: Create agent "Fast Glass SDR" with tools
- [ ] Retell: Configure BYO Twilio (+12135668886)
- [ ] Retell: Upload KB (51 services, FAQ, zones)
- [ ] ROMI: `trigger_callback` tool → Retell API
- [ ] ROMI: Basic conversation monitor in Next.js
- [ ] Redirect Zapier from GHL → ROMI (keep GHL as fallback)

**Cost (estimated 500 leads/mo, 30% accept callback, 3 min avg call):**

| Item | Calculation | Cost |
|------|-------------|------|
| OpenAI GPT-4.1 (SMS brain) | 500 leads × 8 msgs × $0.01 | $40/mo |
| Twilio SMS | 4,000 segments × $0.0079 | $32/mo |
| Retell voice (150 calls × 3 min × $0.10) | 450 min | $45/mo |
| Twilio voice (BYO, 450 min × $0.014) | 450 min | $6/mo |
| Zapier | $0 (Yelp advertiser) | $0 |
| **Total Phase 1** | | **~$123/mo** |

**Success criteria:**
- Callback connect rate > 50%
- 15%+ conversation → booked estimate rate
- Voice AI accurately quotes price ranges (validated by Alex on 20 calls)
- Speed-to-lead < 60s for 95%+ of leads

**Exit criteria → Phase 2:**
- 30 days of production data
- Alex uses ROMI conversation monitor daily
- Yelp partner meeting (July 7) outcome known

---

### Phase 2: Own Backend (Full ROMI Platform) — Months 2–4

**Goal:** Complete Module 10 inside `romi-crm` repo. GHL deprecated for lead response.

**Architecture:** Full 3-layer design from `DESIGN.md`.

**Additional build scope:**
- [ ] PostgreSQL schema (see `DATA_MODEL.md`)
- [ ] pgvector RAG for 51 services
- [ ] Admin UI (see `UI_MOCKUP.md`)
- [ ] Website widget embed
- [ ] Direct Yelp Leads API (if partner status granted July 7)
- [ ] Inbound phone → Retell (same agent)
- [ ] Human takeover flow
- [ ] Analytics dashboard (speed-to-lead, conversion, callback success)
- [ ] HCP integration for `check_availability` / `book_estimate`

**Cost (estimated 1,000 leads/mo, 40% callback, 3 min avg):**

| Item | Calculation | Cost |
|------|-------------|------|
| Railway/VPS (existing) | $0 incremental | $0 |
| PostgreSQL (existing) | $0 incremental | $0 |
| OpenAI (SMS + RAG) | 1,000 × 10 msgs × $0.01 + embeddings | $120/mo |
| Twilio SMS | 10,000 segments × $0.0079 | $79/mo |
| Retell voice (400 calls × 3 min × $0.10) | 1,200 min | $120/mo |
| Twilio voice (BYO) | 1,200 min × $0.014 | $17/mo |
| **Total Phase 2** | | **~$336/mo** |

**Success criteria:**
- GHL no longer needed for lead response
- All channels in unified ROMI inbox
- Alex manages bot persona + KB from ROMI admin (no code deploys)
- Response time KPI on dashboard

**Exit criteria → Phase 3:**
- 3 months stable production
- Playbook documented for onboarding another glass company
- Unit economics validated: cost per booked estimate < $15

---

### Phase 3: SaaS Product — Month 6+

**Goal:** Package AI Lead Responder for other glass/home-services companies.

**Architecture additions:**
- Multi-tenant: `organization_id` on all tables
- Self-serve onboarding: upload KB, connect Yelp/Twilio, configure persona
- White-label widget + SMS number provisioning
- Billing: Stripe per-location + usage (voice minutes, AI messages)
- Consider Vapi over Retell if white-label voice branding needed

**Revenue model (draft):**

| Tier | Price | Includes |
|------|-------|----------|
| Starter | $199/mo per location | SMS AI, 100 voice min |
| Pro | $399/mo per location | + Callback, 500 voice min, analytics |
| Enterprise | Custom | Multi-location, API access, SLA |

**Margin at 500 voice min/mo:**
- Revenue: $399
- COGS: ~$150 (voice + AI + SMS)
- Gross margin: ~62%

---

## Total Cost Comparison (Year 1)

| Approach | Year 1 Cost | Voice Callback | ROMI Integration | Ownership |
|----------|-------------|----------------|------------------|-----------|
| **Hatch** | $6,000–24,000 | ✅ | ❌ Parallel CRM | ❌ |
| **Podium Pro** | $4,800–7,200 | ❌ | ❌ Parallel | ❌ |
| **GHL only** | $1,200–3,600 | ⚠️ Expensive | ❌ | ❌ |
| **Our phased plan** | $3,000–8,000 | ✅ Retell | ✅ Native | ✅ |
| **Build all (no Retell)** | $2,000–5,000 + 8wk dev | ✅ DIY | ✅ Native | ✅ |

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Yelp partner API delayed | Medium | Medium | Zapier bridge works indefinitely |
| Retell pricing increase | Low | Medium | BYO Twilio/LLM; can swap to Vapi |
| AI quotes wrong price | Medium | High | `get_price` tool mandatory; human review first 30 days |
| TCPA violation on callbacks | Low | High | Explicit SMS consent before dial; log timestamps |
| Low callback connect rate | Medium | Medium | Retry SMS; offer text-only path |
| Senya bandwidth (1 dev) | High | Medium | Phase 0 buys 2 weeks; Phase 1 is MVP only |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-14 | Retell over Vapi for Phase 1 | Lower cost, faster setup, built-in KB, 1-dev team |
| 2026-06-14 | GHL for Phase 0 only | Already paid; fastest path to <60s response |
| 2026-06-14 | Reject Hatch/Podium | Cost + CRM lock-in; ROMI is the product |
| 2026-06-14 | OpenAI Realtime deferred to Phase 2+ | Engineering cost too high for Phase 1 |
| 2026-06-14 | Zapier until Yelp partner API | Official bridge; unlimited tasks for advertisers |

---

## Next Actions (for Senya / Alex)

### Immediate (this week)
1. **Alex:** Confirm GHL Conversation AI is configured with Fast Glass FAQ
2. **Senya:** Set up Zapier Zap: Yelp New Lead → GHL (Phase 0)
3. **Alex:** Test with a real Yelp RAQ lead; measure response time

### Week 3 (Phase 1 start)
4. **Senya:** Create Retell account + Fast Glass SDR agent
5. **Senya:** Build ROMI webhook endpoint for Zapier redirect
6. **Alex:** Review 10 AI voice calls for accuracy

### July 7
7. **Alex:** Yelp partner meeting with Jess Greenbaum — ask about direct Leads API access
8. **Senya:** If API granted, plan Phase 2 direct integration

### Month 2
9. **Senya:** Implement `DATA_MODEL.md` schema + basic admin UI
10. **Alex:** Deprecate GHL for lead response once ROMI inbox is live
