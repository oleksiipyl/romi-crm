# ROMI CRM — Professional Development Standards

> This document is the source of truth for how we build.
> Any deviation from this must be flagged and confirmed by Alex before proceeding.
> Last updated: 2026-06-10

---

## 🏗️ CORE PRINCIPLE: Small Tasks, Short Sessions, Always Verified

```
WRONG: "Build the whole CRM"
RIGHT: "Build ONLY the contact create endpoint"

WRONG: 3-hour Cursor session on one feature
RIGHT: 20-30 min focused session → commit → test → next task

WRONG: Deploy and hope it works
RIGHT: Test locally → test on staging → Alex approves → deploy
```

---

## 📋 TASK DISCIPLINE

Every task must have:

```
Title:       [clear, one sentence]
Size:        Small (< 2h) / Medium (2-4h) / Large (> 4h — must be broken down)
Agent:       Who does it (Backend/Frontend/AI/QA)
Input:       What's needed before starting
Output:      Exactly what gets delivered
Test:        How we verify it works
```

**Large tasks MUST be broken into Small/Medium before starting.**
If a task takes more than one Cursor session → it's too big.

---

## 🧠 CONTEXT MANAGEMENT (preventing AI drift)

### Problem
AI agents degrade when context window fills up (200k tokens).
Symptoms: contradictory answers, ignoring previous code, "forgetting" constraints.

### Rules
```
1. One task = one Cursor session
   Start fresh session for each new feature

2. Every session starts with context file:
   "Read /docs/ARCHITECTURE.md and /docs/CURRENT_TASK.md before writing any code"

3. Session limit: 30 minutes max
   If task takes longer → stop, commit what's done, new session

4. CURRENT_TASK.md always updated before session:
   - What we're building
   - What files to touch
   - What NOT to touch
   - Definition of done
```

---

## 🔢 TOKEN & LIMIT MONITORING

### Limits to watch
```
Cursor Pro:    500 fast requests/month (~16/day)
OpenAI API:    budget alert at $10/day
Anthropic API: budget alert at $10/day
```

### Inspector Agent (automated)
Runs every 2 hours via cron:
- Checks API usage
- If >70% of daily budget → Telegram warning ⚠️
- If >90% → Telegram STOP alert 🚨 + pause non-critical agents
- Daily summary at 9am PT

### Manual check command
```bash
python3 /workspace/romi-crm/tools/inspector.py --status
```

---

## 🎨 VISUAL QA — No More Layout Drift

### Problem
Code looks fine on 1920px desktop but breaks on mobile.
Classic bug: hardcoded `width: 1920px` instead of `width: 100%`.

### Rule: Every UI change gets screenshotted before approval

```
After every frontend commit:
1. Playwright takes screenshots at 3 sizes:
   - Desktop: 1440px
   - Tablet:  768px
   - Mobile:  375px
2. Screenshots sent to Telegram
3. Alex reviews visually
4. Only after Alex says OK → merge to main
```

### Visual check command
```bash
python3 /workspace/romi-crm/tools/visual_qa.py --url http://localhost:3000
```

### CSS Rules (enforced by linter)
```css
/* NEVER hardcode pixel widths on containers */
❌ width: 1920px;
❌ width: 1440px;
✅ width: 100%;
✅ max-width: 1440px;
✅ width: 100vw;

/* ALWAYS use responsive units */
✅ Tailwind: w-full, max-w-7xl
✅ Tailwind: px-4 sm:px-6 lg:px-8
```

---

## 🌿 GIT WORKFLOW

```
main branch     = production (always working)
staging branch  = pre-production (tested)
feature/xxx     = new feature (in progress)

Flow:
  feature/contact-list
      ↓ pull request
  staging (test here)
      ↓ Alex approves
  main (deploy)
```

### Commit format
```
✅ feat: add contact create endpoint
✅ fix: mobile menu overflow on 375px
✅ test: add unit tests for pricing engine
❌ "fixed stuff"
❌ "wip"
❌ "asdfgh"
```

### Never commit
- .env files
- API keys
- Database dumps
- node_modules/
- __pycache__/

---

## 🧪 TESTING REQUIREMENTS

### Before any merge to staging:
```
Backend:
  ✅ Unit tests pass (pytest)
  ✅ No hardcoded credentials
  ✅ API returns correct status codes
  ✅ Edge cases handled (empty input, wrong format)

Frontend:
  ✅ No TypeScript errors
  ✅ Visual QA screenshots approved by Alex
  ✅ Works on mobile 375px
  ✅ Works on tablet 768px
  ✅ Works on desktop 1440px
  ✅ Loading states exist
  ✅ Error states exist

Integration:
  ✅ Twilio webhooks tested with real call
  ✅ CallRail webhook tested
  ✅ PDF generation tested
```

### Definition of Bug Severity
```
CRITICAL — blocks release:
  - Data loss
  - Security vulnerability  
  - Payments broken
  - Can't log in
  - Calls not received

HIGH — fix before release:
  - Feature completely broken
  - Layout broken on any screen size
  - Wrong price calculated

MEDIUM — fix in next sprint:
  - Minor UX issue
  - Slow performance

LOW — backlog:
  - Cosmetic issues
  - Nice-to-have improvements
```

---

## 🚀 DEPLOYMENT CHECKLIST

Before every production deploy:
```
□ All tests passing on staging
□ Visual QA approved by Alex
□ No CRITICAL or HIGH bugs open
□ Database migration tested
□ .env variables updated on server
□ Backup taken before deploy
□ Rollback plan ready (last working version known)
□ Alex gives explicit "deploy" approval
```

---

## 💾 BACKUP STRATEGY

```
Database (PostgreSQL):
  - Full backup: every 24 hours → S3
  - Incremental: every 1 hour → S3
  - Retention: 30 days
  - Alert if backup fails → Telegram

Code:
  - GitHub is the backup
  - Every commit = safe point

Files (photos, PDFs):
  - S3 with versioning enabled
  - Retention: 1 year
```

---

## 🚨 WHEN SOMETHING DRIFTS — PROTOCOL

If code quality degrades, context fills, or bugs accumulate:

```
STOP. Do not continue adding features.

1. Senya reports to Alex: "Context drift detected"
2. List all open bugs (CRITICAL + HIGH only)
3. Fix bugs before any new features
4. Start fresh Cursor session with clean context
5. Update CURRENT_TASK.md
6. Resume
```

**Drift warning signs:**
- AI starts contradicting previous code
- New features break existing ones
- Same bug fixed 3+ times
- Code getting longer without getting better

---

## 📊 WEEKLY REVIEW (every Monday)

```
1. What was built last week?
2. What bugs are open?
3. Are we on schedule?
4. Any limit/cost issues?
5. Next week priorities?
```

This keeps the project on track and prevents invisible drift.

---

## 🔧 TOOLS STACK

```
Code:         Cursor (AI-assisted IDE)
Version:      GitHub (oleksiipyl/romi-crm)
Backend:      Python 3.11 + FastAPI
Database:     PostgreSQL (Railway.app)
Frontend:     Next.js 15 + TypeScript + Tailwind
Mobile:       React Native + Expo
Testing:      pytest + Playwright
CI/CD:        GitHub Actions
Hosting:      Railway.app
Storage:      AWS S3
Monitoring:   Custom inspector (Telegram alerts)
```

---

*This document is law. If a decision contradicts it — flag it first.*
*Updated by: Senya | Approved by: Alex*
