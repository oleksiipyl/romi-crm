# AI Lead Responder — Admin UI/UX Mockup

> **Module:** ROMI CRM Module 10  
> **Date:** 2026-06-14  
> **Framework:** Next.js 15 + Tailwind + shadcn/ui (existing ROMI frontend)

---

## Navigation

New top-level section in ROMI dashboard sidebar:

```
📊 Dashboard
📋 Leads
🔧 Jobs
💰 Quotes
📈 Reports
🤖 AI Responder  ← NEW
   ├── Inbox
   ├── Live Monitor
   ├── Analytics
   └── Settings
     ├── Persona
     ├── Knowledge Base
     ├── Channels
     └── Voice Agent
⚙️ Settings
```

**Route structure:**
```
/dashboard/ai-responder/
  /inbox                    # Unified lead inbox
  /inbox/[conversationId]   # Conversation detail
  /monitor                  # Live conversation feed
  /analytics                # Speed-to-lead + conversion
  /settings/persona         # Bot personality config
  /settings/knowledge-base  # KB document management
  /settings/channels        # Yelp, Twilio, widget config
  /settings/voice           # Retell agent config
```

---

## Screen 1: Unified Lead Inbox

**Route:** `/dashboard/ai-responder/inbox`  
**Purpose:** All channels in one view — the Hatch-style command center.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Inbox                                    [⚙️ Settings]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ KPI Bar ──────────────────────────────────────────────────────────────┐ │
│  │  ⏱ Avg Response: 42s   📞 Callbacks Today: 7   ✅ Booked: 3   🟢 Live: 2│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Filters ──────────────────────────────────────────────────────────────┐ │
│  │ [All Channels ▾] [All States ▾] [Today ▾]  🔍 Search leads...         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ● Victor M.          Yelp RAQ    QUALIFY     2m ago    📞 Callback  │   │
│  │   "Sliding patio door glass replacement"                            │   │
│  │   90034 · AI responding · 3 messages                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ ● Sarah K.           SMS         OFFER       5m ago                   │   │
│  │   "How much for a shower door?"                                     │   │
│  │   90210 · AI responding · $450-$800 quoted                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ ○ Mike T.            Website     HUMAN 🧑   12m ago   ✅ Booked     │   │
│  │   "Need mirror cut to size"                                         │   │
│  │   90019 · Alex handling · Estimate Thu 2pm                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ ○ Lisa R.            Yelp RAQ    COMPLETE    1h ago   ✅ Booked     │   │
│  │   "Window won't close, need repair"                                 │   │
│  │   90066 · Booked via voice callback · Estimate Mon 10am             │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ ○ Unknown            SMS         GREET       1h ago   ⚠️ No reply   │   │
│  │   "Do you fix car windows?"                                         │   │
│  │   Out of zone · AI sent greeting · awaiting response                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Showing 5 of 23 conversations                        [← 1 2 3 →]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Inbox Row States

| Indicator | Meaning |
|-----------|---------|
| ● (filled dot) | Active — AI or human responding now |
| ○ (empty dot) | Completed or waiting |
| 🧑 | Human has taken over |
| 📞 | Callback scheduled or in progress |
| ✅ | Booked estimate |
| ⚠️ | Needs attention (no reply, error, out of zone) |

### Channel badges

| Channel | Badge Color | Icon |
|---------|-------------|------|
| Yelp RAQ | Red `#FF1A1A` | Yelp logo |
| SMS | Blue `#2563EB` | 💬 |
| Website | Green `#16A34A` | 🌐 |
| Voice | Purple `#7C3AED` | 📞 |
| Thumbtack | Blue `#009FD4` | TT |

---

## Screen 2: Conversation Detail

**Route:** `/dashboard/ai-responder/inbox/[conversationId]`  
**Purpose:** Full thread view with takeover capability.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back to Inbox                                                            │
├──────────────────────────────┬──────────────────────────────────────────────┤
│                              │                                              │
│  CONVERSATION                │  LEAD DETAILS                                │
│                              │                                              │
│  Victor M.                   │  Name: Victor M.                             │
│  Yelp RAQ · QUALIFY          │  Phone: +1 (310) 555-1234  📋              │
│  Started: 10:30 AM (2m ago)  │  ZIP: 90034 (Palms — ✅ in zone)            │
│  First response: 28s ✅      │  Source: Yelp RAQ                            │
│                              │  Project: Sliding patio door glass           │
│  ┌─ State Machine ────────┐  │                                              │
│  │ GREET → QUALIFY → ○OFFER│  │  Service: Door Installation                │
│  │         ▲ current       │  │  Price range: — (not quoted yet)           │
│  └─────────────────────────┘  │                                              │
│                              │  ┌─ Actions ──────────────────────────────┐  │
│  ┌─ Messages ─────────────┐  │  │ [📞 Trigger Callback]                  │  │
│  │                        │  │  │ [🧑 Take Over]                       │  │
│  │ 10:30 🟡 YELP          │  │  │ [📋 Create Lead in Pipeline]         │  │
│  │ Lead submitted RAQ:    │  │  │ [🚫 Mark as Spam]                    │  │
│  │ "Sliding patio door    │  │  └──────────────────────────────────────┘  │
│  │  glass replacement,    │  │                                              │
│  │  6ft x 8ft"            │  │  ┌─ Callback History ───────────────────┐  │
│  │                        │  │  │ No callbacks yet                     │  │
│  │ 10:30 🤖 AI (28s)      │  │  └──────────────────────────────────────┘  │
│  │ Hi Victor! Thanks for  │  │                                              │
│  │ reaching out through   │  │  ┌─ AI Context ─────────────────────────┐  │
│  │ Yelp about your patio  │  │  │ KB chunks used: 3                    │  │
│  │ door glass — we        │  │  │ • Sliding door glass replacement     │  │
│  │ specialize in exactly  │  │  │ • Service zone 90034                 │  │
│  │ this. I can get you a  │  │  │ • Business hours Mon-Sat             │  │
│  │ ballpark price right   │  │  │ Tokens: 1,240 in / 186 out          │  │
│  │ now, or call you back  │  │  └──────────────────────────────────────┘  │
│  │ in 30 seconds. What    │  │                                              │
│  │ works better?          │  │                                              │
│  │                        │  │                                              │
│  │ 10:31 👤 Victor         │  │                                              │
│  │ "What's the price for  │  │                                              │
│  │  a 6x8 sliding door?"  │  │                                              │
│  │                        │  │                                              │
│  │ 10:31 🤖 AI (4s)       │  │                                              │
│  │ 🔧 get_price(          │  │                                              │
│  │   sliding_door_glass,  │  │                                              │
│  │   72x96, tempered)     │  │                                              │
│  │ → $650-$1,200          │  │                                              │
│  │                        │  │                                              │
│  │ For a 6'x8' tempered   │  │                                              │
│  │ sliding door panel,    │  │                                              │
│  │ you're looking at      │  │                                              │
│  │ $650-$1,200 depending  │  │                                              │
│  │ on the frame condition.│  │                                              │
│  │ Want me to call you in │  │                                              │
│  │ 30 seconds to discuss? │  │                                              │
│  │                        │  │                                              │
│  └────────────────────────┘  │                                              │
│                              │                                              │
│  ┌─ Reply (human mode) ───┐  │                                              │
│  │ Type a message...      │  │                                              │
│  │ [🧑 AI is active — Take Over to reply manually]           │  │
│  └────────────────────────┘  │                                              │
│                              │                                              │
└──────────────────────────────┴──────────────────────────────────────────────┘
```

### Message Types in Thread

| Icon | Type | Display |
|------|------|---------|
| 🟡 | Channel event | Lead submission, Yelp project data |
| 🤖 | AI outbound | Response with latency badge |
| 👤 | Lead inbound | Customer message |
| 🧑 | Human outbound | Alex/team message (after takeover) |
| 🔧 | Tool call | Collapsible: function name + args + result |
| 📞 | Voice transcript | Call summary with recording link |
| ⚙️ | System | State changes, escalations |

### Takeover Flow

1. User clicks **🧑 Take Over**
2. Confirmation modal: "AI will pause. You'll respond manually."
3. `ai_conversations.ai_enabled` → `false`
4. Reply box activates; messages sent as `sender_type: human`
5. **Release to AI** button appears to hand back

---

## Screen 3: Live Monitor

**Route:** `/dashboard/ai-responder/monitor`  
**Purpose:** Real-time feed of AI activity — like a mission control view.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Live Monitor                          🟢 2 active now     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Active Conversations ─────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                    │  │
│  │  │ Victor M. · QUALIFY │  │ Sarah K. · OFFER    │                    │  │
│  │  │ Yelp · 2m 14s       │  │ SMS · 5m 32s        │                    │  │
│  │  │                     │  │                     │                    │  │
│  │  │ 🤖 "For a 6'x8'..." │  │ 🤖 "Shower doors    │                    │  │
│  │  │                     │  │  start at $450..."  │                    │  │
│  │  │ ⏳ Waiting for reply│  │ ⏳ Waiting for reply│                    │  │
│  │  │                     │  │                     │                    │  │
│  │  │ [View] [Take Over]  │  │ [View] [Take Over]  │                    │  │
│  │  └─────────────────────┘  └─────────────────────┘                    │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Activity Feed (real-time) ────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  10:31:42  🤖 AI → Victor M.     get_price → $650-$1,200   (4s)      │  │
│  │  10:31:38  👤 Victor M. → AI     "What's the price for a 6x8..."      │  │
│  │  10:30:58  🤖 AI → Victor M.     Greeting sent              (28s)    │  │
│  │  10:30:30  🟡 NEW LEAD          Victor M. via Yelp RAQ               │  │
│  │  10:28:15  ✅ BOOKED            Lisa R. — Estimate Mon 10am           │  │
│  │  10:27:50  📞 CALLBACK         Lisa R. — 2m 34s call, booked         │  │
│  │  10:25:12  🤖 AI → Sarah K.     "Shower doors start at..."  (3s)    │  │
│  │  10:24:58  🟡 NEW LEAD          Sarah K. via SMS                     │  │
│  │  10:22:00  🧑 TAKEOVER          Mike T. — Alex assumed control       │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Auto-refreshes every 5 seconds (WebSocket in Phase 2)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 4: Analytics Dashboard

**Route:** `/dashboard/ai-responder/analytics`  
**Purpose:** Speed-to-lead KPIs and conversion funnel.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Analytics                    [Last 7 days ▾] [Export]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Speed-to-Lead (Hero KPI) ─────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │   Average First Response          Under 60 seconds                     │ │
│  │   ┌──────────────────┐            ┌──────────────────┐                 │ │
│  │   │                  │            │                  │                 │ │
│  │   │      42s         │            │      94%         │                 │ │
│  │   │   ▼ 18s vs last  │            │   ▲ 12% vs last  │                 │ │
│  │   │      week        │            │      week        │                 │ │
│  │   └──────────────────┘            └──────────────────┘                 │ │
│  │                                                                        │ │
│  │   📊 Response Time Distribution (bar chart)                           │ │
│  │   <30s ████████████████████ 62%                                       │ │
│  │   30-60s ██████████ 32%                                               │ │
│  │   1-5min ███ 4%                                                       │ │
│  │   >5min  █ 2%                                                         │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Conversion Funnel ──────────────┐  ┌─ By Channel ──────────────────┐  │
│  │                                   │  │                                │  │
│  │  Leads Received      156        │  │  Yelp RAQ    89  (57%)        │  │
│  │       ↓ 98%                       │  │  SMS         42  (27%)        │  │
│  │  AI Responded        153        │  │  Website     18  (12%)        │  │
│  │       ↓ 45%                       │  │  Voice        7  (4%)         │  │
│  │  Engaged (2+ msgs)    69        │  │                                │  │
│  │       ↓ 38%                       │  │  (pie chart)                   │  │
│  │  Callback Requested    26        │  │                                │  │
│  │       ↓ 65%                       │  └────────────────────────────────┘  │
│  │  Callback Connected    17        │                                       │
│  │       ↓ 53%                       │  ┌─ Cost Breakdown ──────────────┐  │
│  │  Estimate Booked       23        │  │                                │  │
│  │                                   │  │  OpenAI      $38.20           │  │
│  │  Overall Conversion: 14.7%       │  │  Twilio SMS  $28.40           │  │
│  │                                   │  │  Retell      $42.00           │  │
│  └───────────────────────────────────┘  │  Twilio Voice $5.60           │  │
│                                          │  ─────────────────            │  │
│  ┌─ Callback Performance ───────────┐   │  Total        $114.20         │  │
│  │                                   │   │  Cost/booked  $4.97           │  │
│  │  Connect Rate:    65%  (17/26)   │   └────────────────────────────────┘  │
│  │  Avg Duration:    3m 12s         │                                       │
│  │  Booked on Call:  8/17 (47%)     │                                       │
│  │  Handoff:         3/17 (18%)     │                                       │
│  │  No Answer:       6/26 (23%)     │                                       │
│  └───────────────────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 5: Settings — Persona

**Route:** `/dashboard/ai-responder/settings/persona`

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Settings > Persona                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Bot Name                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Fast Glass Assistant                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Persona Prompt (system instructions)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ You are the AI assistant for Fast Glass & Windows, a trusted glass   │   │
│  │ repair and replacement company serving the greater Los Angeles area. │   │
│  │                                                                       │   │
│  │ RULES:                                                                │   │
│  │ 1. Be warm, professional, and concise. Use the lead's first name.    │   │
│  │ 2. NEVER quote exact prices without calling the get_price tool.      │   │
│  │ 3. Always mention we can call them back in about 30 seconds.         │   │
│  │ ...                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ Behavior ─────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  Response delay:     [2] seconds    (feels more human)                │ │
│  │  Callback delay:     [30] seconds   (after consent)                   │ │
│  │  Max AI messages:    [20]           (before auto-escalate)            │ │
│  │  Chat model:         [GPT-4.1 ▾]                                      │ │
│  │                                                                        │ │
│  │  Auto-escalate keywords:                                              │ │
│  │  [emergency] [broken] [shattered] [injured] [+ Add]                   │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Business Hours ─────────────────────────────────────────────────────┐ │
│  │  Mon-Fri:  [08:00] – [18:00]   Sat: [09:00] – [15:00]   Sun: Closed │ │
│  │                                                                        │ │
│  │  After-hours message:                                                 │ │
│  │  [Thanks for reaching out! We're closed but I can still help...]     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Test Bot ─────────────────────────────────────────────────────────────┐ │
│  │  [Type a test message...]                              [Send Test]    │ │
│  │                                                                        │ │
│  │  🤖 "Hi! Thanks for contacting Fast Glass & Windows..."              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                              [Cancel]  [Save Changes]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 6: Settings — Knowledge Base

**Route:** `/dashboard/ai-responder/settings/knowledge-base`

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Settings > Knowledge Base              [+ Upload Doc]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [All ▾] [Services] [Zones] [FAQ] [Hours] [Policies]     🔍 Search...   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 📄 51-Service Pricing Catalog        services   ✅ Active  v3     │   │
│  │    51 chunks · Last updated: Jun 10 · CSV import                   │   │
│  │    [View Chunks] [Re-import] [Deactivate]                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 📄 LA Metro Service Zones              zones      ✅ Active  v1     │   │
│  │    15 chunks · ZIP codes 90001-90899                                 │   │
│  │    [View Chunks] [Edit] [Deactivate]                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 📄 Frequently Asked Questions          faq       ✅ Active  v2     │   │
│  │    28 chunks · Insurance, warranty, timeline questions               │   │
│  │    [View Chunks] [Edit] [Deactivate]                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 📄 Business Hours & Availability       hours     ✅ Active  v1     │   │
│  │    1 chunk · Mon-Sat schedule + emergency policy                     │   │
│  │    [Edit] [Deactivate]                                               │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 📄 Deposit & Cancellation Policy       policies  ✅ Active  v1     │   │
│  │    3 chunks · 50% deposit, 24hr cancellation                         │   │
│  │    [Edit] [Deactivate]                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ Upload New Document ──────────────────────────────────────────────┐  │
│  │  Drag & drop PDF, TXT, CSV or click to browse                       │  │
│  │  Category: [FAQ ▾]   Title: [________________]                       │  │
│  │                                          [Upload & Process]          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 7: Settings — Channels

**Route:** `/dashboard/ai-responder/settings/channels`

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Settings > Channels                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Yelp (via Zapier) ──────────────────────────────── ✅ Connected ───┐  │
│  │  Webhook URL: https://crm.fastglass.com/api/v1/ai-responder/        │  │
│  │               webhooks/zapier/yelp                                     │  │
│  │  [📋 Copy]                                                            │  │
│  │                                                                        │  │
│  │  Triggers: New Lead ✅ · New Message ✅ · Phone Availability ✅       │  │
│  │  Last event: 2 minutes ago · 89 leads this month                      │  │
│  │                                                                        │  │
│  │  ⚠️ Direct API: Pending partner status (meeting Jul 7)                │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ SMS (Twilio) ───────────────────────────────────── ✅ Connected ───┐  │
│  │  Number: +1 (213) 566-8886                                           │  │
│  │  Webhook: /api/v1/ai-responder/webhooks/twilio/sms                    │  │
│  │  42 conversations this month                                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Website Widget ──────────────────────────────────── ✅ Active ──────┐  │
│  │  Embed code:                                                          │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │ <script src="https://app.fastglass.com/widget/ai-responder.js" │  │  │
│  │  │   data-business-id="fast-glass-la"></script>                   │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │  [📋 Copy]                                                            │  │
│  │  18 conversations this month · Preview: [Open Widget Preview]         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Thumbtack ──────────────────────────────────────── ⏳ Coming Soon ──┐  │
│  │  No public API available. Email parsing integration planned Phase 2.  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Google LSA ─────────────────────────────────────── ⏳ Coming Soon ──┐  │
│  │  Lead form webhook via Zapier planned Phase 2.                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 8: Settings — Voice Agent

**Route:** `/dashboard/ai-responder/settings/voice`

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Responder > Settings > Voice Agent                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Provider: Retell AI                              Status: ✅ Connected      │
│  Agent ID: agent_fastglass_sdr                                              │
│                                                                             │
│  ┌─ Voice Settings ─────────────────────────────────────────────────────┐  │
│  │  Voice:     [Adrian (ElevenLabs) ▾]                                   │  │
│  │  Language:  [English (US) ▾]                                          │  │
│  │  Speed:     [1.0x ▾]                                                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Callback Settings ──────────────────────────────────────────────────┐  │
│  │  From number:     +1 (213) 566-8886 (BYO Twilio)                      │  │
│  │  Delay after consent: [30] seconds                                    │  │
│  │  Max attempts:        [3]                                               │  │
│  │  Retry after no-answer: [5] minutes (via SMS)                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Warm Transfer ────────────────────────────────────────────────────┐  │
│  │  Transfer to:  [Alex — +1 (310) 555-0100 ▾]                           │  │
│  │  Fallback:     [On-call tech — +1 (310) 555-0101 ▾]                   │  │
│  │  Transfer message: "Let me connect you with our team now."            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Voice Prompt (Retell LLM) ─────────────────────────────────────────┐  │
│  │  [You are the AI phone assistant for Fast Glass & Windows...]        │  │
│  │  (Synced with Retell agent — edits here update via API)              │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Test Call ──────────────────────────────────────────────────────────┐  │
│  │  Phone: [+1 (___) ___-____]                        [📞 Test Call Me]  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Cost Tracker (this month) ──────────────────────────────────────────┐  │
│  │  Calls: 47 · Minutes: 142 · Avg: 3m 01s · Cost: $14.20 (Retell)     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                                              [Cancel]  [Save Changes]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Mobile Responsive Notes

- **Inbox:** Card layout on mobile (stacked, swipe for actions)
- **Conversation detail:** Full-screen thread; lead details in bottom sheet
- **Takeover:** Prominent floating button on mobile
- **Analytics:** KPI cards stack vertically; charts scroll horizontally
- **Settings:** Accordion sections on mobile

---

## Component Mapping (shadcn/ui)

| UI Element | shadcn Component |
|------------|------------------|
| Inbox list | `Card` + `Badge` + `Avatar` |
| Conversation thread | Custom `MessageBubble` (extend `Card`) |
| State machine indicator | Custom `StepIndicator` |
| KPI cards | `Card` + `CardHeader` + `CardContent` |
| Filters | `Select` + `Input` + `Button` |
| Charts | Recharts (`BarChart`, `PieChart`, `FunnelChart`) |
| Settings forms | `Form` + `Textarea` + `Input` + `Switch` |
| Takeover modal | `AlertDialog` |
| Activity feed | `ScrollArea` + custom `FeedItem` |
| Channel status | `Badge` (green/yellow/red) |

---

## Widget Preview (Website Embed)

```
┌──────────────────────────────┐
│  Fast Glass & Windows    ✕  │
│  ─────────────────────────── │
│                              │
│  🤖 Hi! I'm the Fast Glass   │
│  assistant. How can I help   │
│  with your glass needs?      │
│                              │
│  ┌────────────────────────┐  │
│  │ Window repair          │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ Shower door            │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ Get a quote            │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │ Type a message...    ➤ │  │
│  └────────────────────────┘  │
│                              │
│  💬 Prefer text? Leave your  │
│  number for a quick reply.   │
└──────────────────────────────┘
         ↑
    Floating button (bottom-right):
    ┌──────┐
    │ 💬   │
    │ Chat │
    └──────┘
```

Widget colors: ROMI blue `#2563EB` accent, white background, matches existing dashboard theme.
