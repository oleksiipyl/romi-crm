# ROMI Estimate — Agent Coordination Protocol

> Same rules as ROMI CRM: **SYNC → OPEN → work → CLOSE**.
> Separate repo — own lock file. Does not block `romi-crm`.

**Target repo:** `github.com/oleksiipyl/romi-estimate` (or your estimate branch)

---

## Identity (same as CRM)

```
OpenClaw  =  Senya   (Tech Lead, Alex's main contact)
Cursor Cloud  =  Senya's repo agent for ROMI Estimate
```

Alex → Senya (OpenClaw). Senya assigns Estimate work → Cursor Cloud in `docs/CURRENT_TASK.md`.

---

## Project context

| Item | Value |
|------|-------|
| Product | ROMI Estimate — field glass price calculator |
| Stack | FastAPI + SQLite + plain HTML (mobile-first PWA) |
| Pricing source | Port logic from `bot_correct.py` |
| Spec | See `ESTIMATE_APP_IDEA.md` in romi-crm repo (or copy to estimate `/docs/`) |
| CRM link | Later: saves leads/quotes to ROMI CRM (Phase 3+) |

**Do not mix** CRM and Estimate code in one repo.

---

## SYNC → OPEN → CLOSE

Every session, in order:

### 1. SYNC
```bash
git pull origin main   # or your active branch
cat docs/CURRENT_TASK.md
```

### 2. OPEN (acquire lock)
If `lock_holder` is `none`:

```yaml
lock_holder: cursor-cloud   # or openclaw when Senya works locally
lock_since: 2026-06-11T12:00:00Z
lock_task: "Short description"
status: in_progress
```

```bash
git add docs/CURRENT_TASK.md
git commit -m "🔒 Lock acquired by cursor-cloud: <task>"
git push
```

If lock held by **other** agent → **STOP**. Read Last handoff only.

### 3. Work
- One small task per session
- Branches: `cursor/<task-name>-68b2`
- ASK → PLAN → BUILD (major changes need Alex OK)

### 4. CLOSE (release lock)
```yaml
lock_holder: none
lock_since: null
lock_task: null
status: idle
```

Fill **Last handoff**: done, next, branch/PR.

```bash
git commit -m "🔓 Handoff from cursor-cloud: <summary>"
git push
```

---

## Lock IDs (this repo only)

| ID | Who |
|----|-----|
| `openclaw` | Senya |
| `cursor-cloud` | Cursor Cloud repo agent |
| `none` | Idle |

---

## Cross-repo rule

| Repo | Lock file |
|------|-----------|
| `romi-crm` | `romi-crm/docs/CURRENT_TASK.md` |
| `romi-estimate` | `romi-estimate/docs/CURRENT_TASK.md` |

Senya may work on CRM while Cursor works on Estimate — **different repos, different locks**.

Within **one** repo: still only one agent at a time.

---

## Bootstrap (first time in romi-estimate)

If `docs/CURRENT_TASK.md` does not exist yet, create:

1. `docs/AGENT_COORDINATION.md` — copy from this file
2. `docs/CURRENT_TASK.md` — lock idle
3. `docs/ESTIMATE_APP_IDEA.md` — copy from romi-crm or link
4. `docs/DECISIONS_LOG.md` — estimate-specific decisions

Then OPEN lock and proceed.

---

*Mirror of ROMI CRM coordination — 2026-06-11*
