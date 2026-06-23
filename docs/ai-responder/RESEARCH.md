# AI Lead Responder — Competitor Research (Phase 1)

> **Module:** ROMI CRM Module 10 — AI Agent (24/7 voice + SMS)  
> **Date:** 2026-06-14  
> **Scope:** Research only — no production code

---

## Executive Summary

The market splits into three categories relevant to Fast Glass:

| Category | Players | Best for |
|----------|---------|----------|
| **Vertical home-services SDR** | Hatch, Podium | Turnkey speed-to-lead for contractors; high monthly fees, sales-led onboarding |
| **Voice AI infrastructure** | Vapi, Retell, Bland, OpenAI Realtime | Programmable outbound/inbound voice; per-minute billing |
| **Conversation design + automation** | GoHighLevel, Voiceflow | Workflow builders, SMS/chat automation, CRM-adjacent |

**Key takeaway for ROMI CRM:** Hatch and Podium prove the UX patterns (unified inbox, instant AI reply, warm handoff, campaign triggers). Vapi/Retell/Bland provide the voice callback layer. GHL is a useful Phase 0 bridge while ROMI is built. **Retell AI is the recommended voice provider for Phase 1** (see `DESIGN.md` § Voice Callback).

---

## Speed-to-Lead: Why This Matters

| Study | Finding | Source |
|-------|---------|--------|
| Velocify (3.5M+ leads) | Calling within **1 minute** increases conversion by **391%** vs slower response | [Velocify Ultimate Contact Strategy](https://appexchange.salesforce.com/partners/servlet/servlet.FileDownload?file=00P3000000P3dgaEAB) |
| Velocify | Advantage decays fast: +160% at 2 min, +98% at 3 min, +62% at 30 min | Same study |
| Harvard Business Review | Companies responding within **5 minutes** are **100×** more likely to connect than those waiting 30 min | Cited in [Rogue Digital analysis](https://www.roguedigital.ai/insights/response-time-conversions) |
| Industry audit | Only **7%** of businesses actually call within 1 minute | [Velocify "Faster is Better" report](https://vfp.us/wp-content/uploads/2020/08/Faster-is-better_HotLeadNotification.pdf) |

Fast Glass currently waits **13+ hours** on some Yelp leads. Even a 60-second AI text + optional 30-second voice callback would move them from bottom 7% to top tier.

---

## Competitor Deep Dives

### 1. Hatch (usehatchapp.com / usehatch.ai)

**Positioning:** AI growth engine for home services — voice, SMS, email in one platform. 2,000+ customers.

#### Core UX Patterns
- **Campaign → AI → Human handoff:** CRM triggers fire outreach; AI handles replies; humans step in with full context on a single contact card.
- **Multi-inbox command center:** All conversations (voice transcripts, SMS, email) in one workspace with visual boards.
- **Named AI agents:** Each bot has a name, personality, and directive (qualify, book, follow up on quote).
- **Context from FSM:** Pulls in-home visit details from ServiceTitan etc. for personalized follow-up ("your $9,400 condenser quote").
- **Warm transfer:** Voice AI can transfer to live CSR with transcript attached.

#### Voice Callback / Speed-to-Lead
- AI voice answers inbound 24/7 and can **initiate outbound** as part of journey campaigns.
- Demo CTA: "An AI agent will call you within a minute."
- Native integrations: ServiceTitan, Yelp, Angi.

#### Knowledge Base / Context
- White-glove AI setup — not self-serve KB upload.
- Templates for home-services playbooks (estimate follow-up, win-back, lead response).
- Business directive + CRM field injection rather than open RAG.

#### Pricing
| Tier | Model | Notes |
|------|-------|-------|
| Standard | Platform fee + usage, annual contract | Demo-gated; no public list price |
| Pro | Same + more contacts/AI convos | Custom reporting, marketing blasts |
| Enterprise | Multi-location, rich analytics | Sales-led |

Operator reports: **mid-market pricing**, meaningfully above ~$300/mo tools like CHIIRP. Per-location billing.

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Single contact card across channels | Annual-only contracts before product-market fit |
| Campaign triggers from CRM events | Opaque pricing requiring sales calls |
| AI persona with business directive | Lock-in to their CRM instead of ROMI |
| Warm transfer with transcript | White-glove-only setup (we need self-serve admin) |

---

### 2. Podium (podium.com)

**Positioning:** AI-powered lead conversion for local businesses — reviews + messaging + AI concierge.

#### Core UX Patterns
- **Unified inbox:** SMS, webchat, Google Business Profile, Facebook in one thread.
- **AI Concierge (Pro):** Auto-qualifies inbound text leads, books appointments.
- **AI Reputation Specialist:** Drafts review responses.
- **AI Phone Call Summaries:** Transcribes and condenses calls.
- **Lead capture forms** + automatic lead routing.

#### Voice Callback / Speed-to-Lead
- Primarily **text-first**; voice is summarization, not AI voice agent.
- No native "call back in 30 seconds" voice AI — relies on human follow-up after AI text qualification.
- 200+ integrations via marketplace.

#### Knowledge Base / Context
- AI trained on business profile + FAQ; less transparent than developer platforms.
- Industry-specific tuning (auto, healthcare, furniture).

#### Pricing (2026 estimates — quote-based)
| Plan | Price | Key AI Features |
|------|-------|-----------------|
| Core | ~$399/mo | 250 bulk credits, 5 phone numbers, 2 locations |
| Pro | ~$599/mo | AI Concierge, AI Reputation, 500 credits, 15 numbers |
| Signature | Custom | Unlimited locations, enterprise |

Add-ons: $5/mo 10DLC per location, $5/mo extra numbers, 12-month contracts typical.

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Unified inbox UX | $400–600/mo for features we can build cheaper |
| AI lead qualification via text | Review-management bundle we don't need |
| Multi-channel lead consolidation | Quote-only pricing model |

---

### 3. Vapi (vapi.ai)

**Positioning:** Developer-first voice AI orchestration — API control over STT, LLM, TTS, telephony.

#### Core UX Patterns
- **Assistant JSON config:** Define prompts, tools, voice, model via API or dashboard.
- **Per-call cost breakdown:** Shows exactly what each layer cost.
- **Tool calling:** HTTP functions, transfers, end-call, DTMF.
- **Squads:** Multi-assistant handoffs within one call.

#### Voice Callback / Speed-to-Lead
- **Outbound via `POST /call`:** Programmatic dial-out with assistant attached.
- Webhook events: `call-started`, `call-ended`, `tool-calls`, `transcript`.
- Supports Twilio, Vonage, Telnyx BYO telephony.
- No visual campaign builder — requires custom orchestration in your backend.

#### Knowledge Base / Context
- File upload + `knowledgeBaseId` on assistant.
- Provider pass-through: Deepgram STT + OpenAI LLM + ElevenLabs TTS (you choose stack).

#### Pricing (2026)
| Component | Cost |
|-----------|------|
| Vapi platform fee | **$0.05/min** |
| STT (Deepgram) | ~$0.01/min |
| LLM (GPT-4o) | ~$0.03–0.06/min |
| TTS (ElevenLabs) | ~$0.02–0.04/min |
| Telephony (Twilio US) | ~$0.014/min |
| **Typical total** | **$0.14–0.25/min** (can reach $0.33+) |
| SMS/Chat | $0.005/message |
| Concurrency add-on | ~$10/line/month |
| HIPAA add-on | $2,000/mo |
| Free credits | $10 on signup |

Plans: **Build** (pay-as-you-go), **Scale** (annual, custom), **Enterprise**.

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Tool-calling architecture for CRM functions | Component billing complexity for a 1-person tech team |
| Webhook-driven call lifecycle | Building everything on Vapi when Retell is simpler for Phase 1 |
| BYO Twilio (Fast Glass already has Twilio) | $2K/mo HIPAA we don't need yet |

---

### 4. Retell AI (retellai.com)

**Positioning:** Voice-first AI agents with built-in telephony, KB, and lower ops overhead.

#### Core UX Patterns
- **Agent dashboard:** Visual agent builder with prompt, voice, LLM, tools.
- **LLM Response Engine:** Optimized for voice latency (~600ms).
- **Built-in analytics:** Call success, latency, sentiment.
- **Webhook + API:** `POST /v2/create-phone-call` for outbound.

#### Voice Callback / Speed-to-Lead
- **Outbound call API:**
  ```http
  POST https://api.retellai.com/v2/create-phone-call
  Authorization: Bearer <RETELL_API_KEY>
  {
    "from_number": "+12135668886",
    "to_number": "+13105551234",
    "override_agent_id": "agent_fastglass_sdr",
    "retell_llm_dynamic_variables": {
      "lead_name": "Victor",
      "service_type": "sliding door glass",
      "yelp_project": "Replace broken patio door panel"
    }
  }
  ```
- **Warm transfer:** `transfer_call` tool → Twilio conference to Alex/tech.
- **BYO Twilio:** $0/min Retell telephony surcharge (Fast Glass saves $0.015/min).

#### Knowledge Base / Context
- Upload PDFs/docs → attach to agent → **$0.005/min** when KB active (first 10 free).
- `retell_llm_dynamic_variables` inject lead context per call without re-indexing.

#### Pricing (2026 — from retellai.com/pricing)
| Component | Cost |
|-----------|------|
| Voice infra | $0.055/min |
| TTS (standard voices) | $0.015/min |
| LLM (GPT-4.1 mini) | $0.016/min |
| LLM (GPT-5 nano) | $0.003/min |
| Telephony (Retell Twilio) | $0.015/min |
| Telephony (BYO Twilio) | **$0.00/min** |
| Knowledge Base | +$0.005/min |
| Phone number | $2/mo (or BYO) |
| **Fast Glass realistic (BYO Twilio, GPT-4.1 mini, KB)** | **~$0.09–0.11/min** |
| Free tier | $10 credits, 20 concurrent calls |

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Outbound API with dynamic variables | Premium LLMs (GPT-5.4) unless needed — cost adds up |
| Built-in KB for 51 services FAQ | Retell-managed Twilio when we have BYO |
| Warm transfer tool | Over-engineering custom STT/LLM/TTS when Retell bundles it |

**→ Recommended for Phase 1 voice callback.** See `DESIGN.md` §4.

---

### 5. Bland AI (bland.ai)

**Positioning:** Enterprise voice AI with all-in per-minute pricing (no provider pass-through).

#### Core UX Patterns
- **Pathways:** Visual conversation flow builder (similar to Voiceflow).
- **Custom voices:** Voice cloning (1–15 clones by tier).
- **Batch campaigns:** Outbound at scale.
- **BYOT (Bring Your Own Twilio):** Transfer fees waived.

#### Voice Callback / Speed-to-Lead
- `POST https://api.bland.ai/v1/calls` with `phone_number`, `task`, `voice_id`.
- Supports inbound + outbound + transfers.
- Pathway-based scripting for deterministic qualification steps.

#### Knowledge Base / Context
- 10–100 knowledge bases by plan.
- `task` prompt + `request_data` for per-call variables.

#### Pricing (Dec 2025 restructure)
| Plan | Subscription | Per Minute | Limits |
|------|-------------|------------|--------|
| Start | $0 | $0.14/min | 100 calls/day, 10 concurrent |
| Build | $299/mo | $0.12/min | 2,000 calls/day, 50 concurrent |
| Scale | $499/mo | $0.11/min | 5,000 calls/day, 100 concurrent |
| Enterprise | Custom | Custom | Unlimited |

Add-ons: $0.015/outbound attempt minimum, transfer $0.03–0.05/min (free with BYOT), SMS $0.02/msg.

**Example:** 1,000 min/mo on Build + BYOT ≈ **$423/mo** ($299 + $120 usage).

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| All-in pricing predictability | $299/mo platform fee before ROMI is live |
| Pathway visual flows (inspiration for our state machine) | Developer-heavy API vs Retell's faster setup |
| BYOT transfer fee waiver | Start tier $0.14/min — most expensive for low volume |

---

### 6. GoHighLevel (gohighlevel.com)

**Positioning:** Agency CRM + automation platform. Fast Glass already has GHL (12 numbers).

#### Core UX Patterns
- **Conversation AI:** Chatbot trained on business KB; $0.02/message pay-per-use.
- **Workflows:** Visual automation (trigger → action → wait → branch).
- **Sub-accounts:** Per-location isolation.
- **LeadConnector:** Native Zapier-like integrations.

#### Voice Callback / Speed-to-Lead
- **Voice AI (inbound):** Included in AI Employee Unlimited ($97/mo/sub-account).
- **Voice AI Outbound:** Pay-per-use only (~$0.13/min voice engine + AI); NOT in Unlimited plan.
- No native "30-second callback" UX — must build workflow: SMS consent → Voice AI outbound action.

#### Knowledge Base / Context
- Upload docs to Conversation AI / Voice AI agent settings.
- Workflow AI premium actions: Intent Detection $0.01/execution.

#### Pricing (2026)
| Item | Cost |
|------|------|
| Starter plan | $97/mo |
| Unlimited plan | $297/mo |
| Agency Pro (SaaS rebilling) | $497/mo |
| Conversation AI | $0.02/msg OR $97/mo unlimited per sub-account |
| Voice AI | ~$0.163/min (pay-per-use) |
| AI Employee Growth | $50/mo — 1,000 agent responses + 100 voice min |
| AI Employee Unlimited | $97/mo — unlimited Conversation AI + inbound Voice AI |
| SMS (Twilio pass-through) | $0.0079/segment |
| Outbound calls | $0.014/min |

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Phase 0 text autoresponse via existing GHL | Building long-term on GHL instead of ROMI |
| Workflow trigger patterns (new lead → AI reply) | $97/mo × N sub-accounts AI cost trap |
| 12 existing phone numbers for SMS | GHL Voice AI outbound (expensive, limited) |

**→ Recommended for Phase 0 only.** Bridge until ROMI Module 10 is live.

---

### 7. Voiceflow (voiceflow.com)

**Positioning:** Conversational AI design platform — visual flow builder for chat + voice.

#### Core UX Patterns
- **Canvas editor:** Drag-and-drop conversation flows with LLM blocks, conditions, API calls.
- **Agent CMS:** Knowledge base management with 3,000–10,000 sources.
- **Environments:** Dev → staging → production pipelines.
- **Post-automation workflows:** CRM update after conversation ends (reduces Zapier need).

#### Voice Callback / Speed-to-Lead
- Voice via Twilio/Vonage integration (telephony billed separately).
- ~10 credits/minute for voice; agents stop when credits exhausted.
- Not optimized for sub-30-second outbound callback — better for designed inbound flows.

#### Knowledge Base / Context
- RAG with document upload, URL scraping, API data sources.
- Per-message cost transparency in builder.

#### Pricing (2026)
| Plan | Price | Credits | Agents |
|------|-------|---------|--------|
| Starter | Free | 100 | 2 |
| Pro | $60/mo/editor | 10,000 | 20 |
| Business | $150/mo/editor | 30,000 | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited |

Extra editor: $50/mo. Voice telephony (Twilio) billed separately (~$0.01–0.03/min).

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Visual conversation designer (inspiration for admin UI) | Credit-based billing that halts agents mid-conversation |
| Post-conversation CRM webhook pattern | Using Voiceflow as production voice layer |
| Environment promotion (dev/staging/prod) | Per-editor seat costs for team |

---

### 8. OpenAI Realtime API

**Positioning:** Low-latency speech-to-speech model for custom voice apps.

#### Core UX Patterns
- **WebSocket session:** `wss://api.openai.com/v1/realtime` with audio stream in/out.
- **Function calling:** Same tool pattern as Chat Completions.
- **GPT-Realtime-2:** GPT-5-class reasoning in voice (May 2026).

#### Voice Callback / Speed-to-Lead
- **No telephony included.** You must build: Twilio Media Streams ↔ OpenAI Realtime bridge.
- Significant engineering: VAD, interruption handling, reconnect logic, recording.
- Best for Phase 2+ when ROMI owns the full voice stack.

#### Knowledge Base / Context
- Inject via system prompt + RAG results as conversation items.
- Cached input tokens: $0.40/1M (90%+ savings on repeated context).

#### Pricing (June 2026 — openai.com/api/pricing)
| Model | Pricing | ~Per Minute |
|-------|---------|-------------|
| GPT-Realtime-2 audio input | $32/1M tokens | ~$0.077/min |
| GPT-Realtime-2 audio output | $64/1M tokens | ~$0.154/min |
| **Typical conversation** | — | **~$0.23/min** |
| GPT-Realtime-Translate | $0.034/min flat | Translation only |
| GPT-Realtime-Whisper | $0.017/min flat | Transcription only |

Plus Twilio telephony (~$0.014/min outbound) → **~$0.25/min all-in** if self-built.

#### Copy vs Avoid

| ✅ Copy | ❌ Avoid |
|---------|----------|
| Tool-calling pattern (same as our SMS brain) | Building Realtime bridge in Phase 0/1 |
| GPT-4.1/5 for text brain (already in ROMI stack) | Token billing unpredictability on long calls |
| Future Phase 2 voice ownership | Ignoring Retell/Vapi while building custom |

---

## Feature Comparison Matrix

| Feature | Hatch | Podium | Vapi | Retell | Bland | GHL | Voiceflow | OpenAI RT |
|---------|-------|--------|------|--------|-------|-----|-----------|-----------|
| Instant SMS reply | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| AI voice outbound | ✅ | ❌ | ✅ | ✅ | ✅ | ⚠️ PPU | ⚠️ | 🔧 DIY |
| Visual flow builder | ✅ | ⚠️ | ❌ | ⚠️ | ✅ | ✅ | ✅ | ❌ |
| Tool/API calling | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| BYO Twilio | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Home-services templates | ✅ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ |
| Self-serve pricing | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Unified inbox | ✅ | ✅ | ❌ | ⚠️ | ❌ | ✅ | ❌ | ❌ |
| Warm transfer | ✅ | ❌ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | 🔧 |
| ~Cost per voice min | Opaque | N/A | $0.14–0.25 | $0.09–0.11 | $0.11–0.14 | $0.16+ | Credits+Twilio | $0.25+ DIY |

---

## Patterns to Implement in ROMI CRM

### From vertical players (Hatch, Podium)
1. **Unified lead inbox** — all channels → one thread per contact
2. **Speed-to-lead dashboard** — response time as primary KPI
3. **AI → human handoff** — one click takeover with full transcript
4. **Source attribution** — Yelp / web / SMS / voice tagged per message

### From voice infra (Retell, Vapi)
1. **Outbound callback API** — consent → 30s delay → `create-phone-call`
2. **Dynamic variables** — inject lead name, service, Yelp project per call
3. **Tool calling** — `get_price`, `book_estimate`, `escalate_to_human`
4. **Webhook lifecycle** — `call_started`, `call_ended`, `call_analyzed`

### From automation (GHL, Voiceflow)
1. **Workflow triggers** — `lead.created` → AI greet → wait for reply → branch
2. **KB management UI** — upload docs, set service zones, pricing rules
3. **Environment promotion** — test bot in staging before production

---

## Sources

- [Hatch Pricing](https://www.usehatchapp.com/pricing)
- [Hatch Docs — What is Hatch](https://docs.usehatchapp.com/getting-started/intro-to-hatch/what-is-hatch)
- [Podium Pricing (PulseSignal)](https://getpulsesignal.com/pricing/podium)
- [Vapi Pricing Docs](https://github.com/VapiAI/docs/blob/main/fern/pricing.mdx)
- [Retell AI Pricing](https://www.retellai.com/pricing)
- [Bland AI Pricing](https://www.bland.ai/pricing)
- [Bland Billing Docs](https://docs.bland.ai/platform/billing)
- [GoHighLevel AI Pricing](https://help.gohighlevel.com/support/solutions/articles/155000006652-ai-product-pricing)
- [Voiceflow Pricing](https://www.voiceflow.com/pricing)
- [OpenAI API Pricing](https://openai.com/api/pricing/)
- [Yelp Leads API — Zapier](https://docs.developer.yelp.com/docs/leads-api-zapier-integration)
- [Velocify Speed-to-Call Study](https://cdn2.hubspot.net/hubfs/69576/leads360_wp_speed_to_call.pdf)
