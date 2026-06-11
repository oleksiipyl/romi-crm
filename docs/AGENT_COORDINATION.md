# ROMI CRM — Agent Coordination Protocol

> How **Cursor Cloud Agent** and **OpenCloud Agent** work together without conflicts.
> GitHub repo is the single source of truth for status and handoffs.

---

## Two Agents, One Repo

```
                    ┌─────────────────┐
                    │   ALEX (Human)  │
                    │  Product Owner  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼─────────┐         ┌─────────▼─────────┐
    │  CURSOR CLOUD     │         │    OPENCLOUD      │
    │  Agent (Chief)    │◄───────►│    Agent          │
    │  GitHub + PRs     │  git    │  Mac Mini / local │
    └─────────┬─────────┘         └─────────┬─────────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
                    github.com/oleksiipyl/romi-crm
                    docs/CURRENT_TASK.md  ← lock + handoff
```

| Agent | Platform | Primary role |
|-------|----------|--------------|
| **Cursor Cloud** | Cursor Cloud Agent | Chief orchestrator. GitHub, PRs, architecture, docs, cloud implementation |
| **OpenCloud** | OpenCloud / Mac Mini | Local dev, running services, porting `bot_correct.py` / `voice_handler.py`, local testing |

**Rule: only ONE agent works at a time.** The other waits or reads only.

---

## Lock File: `docs/CURRENT_TASK.md`

Before any code or doc changes:

1. `git pull origin main` (or your active branch)
2. Read `docs/CURRENT_TASK.md`
3. If `lock_holder` is **not** `none` and **not** your agent ID → **STOP**. Do not edit files.
4. If lock is free → acquire lock (see below), commit, push, then start work.

### Acquire lock

Update `docs/CURRENT_TASK.md`:

```yaml
lock_holder: cursor-cloud   # or opencloud
lock_since: 2026-06-11T12:00:00Z
lock_task: "Short description of what you are doing"
status: in_progress
```

Commit message: `🔒 Lock acquired by <agent-id>: <task>`

Push immediately so the other agent sees the lock.

### Release lock (handoff)

When finished (or stopping mid-task):

```yaml
lock_holder: none
lock_since: null
lock_task: null
status: idle
```

Fill in **Last handoff** section with:
- What was completed
- What is next
- Which agent should pick up next (if known)
- Branch name / PR link if applicable

Commit message: `🔓 Handoff from <agent-id>: <summary>`

Push immediately.

---

## Session Workflow

```
START
  │
  ├─► git pull
  ├─► Read CURRENT_TASK.md
  │
  ├─► Lock held by other? ──YES──► STOP (read handoff only)
  │
  NO
  │
  ├─► Acquire lock → commit → push
  ├─► Read ARCHITECTURE.md + CURRENT_TASK.md
  ├─► Do work (one small task per session)
  ├─► Commit + push incrementally
  ├─► Release lock + handoff notes → commit → push
  │
END
```

---

## Conflict Prevention

### Git rules

- **Never** force-push to `main`
- Work on feature branches: `cursor/<name>-68b2` (Cloud) or `opencloud/<name>` (OpenCloud)
- Merge via PR only; chief (Cursor Cloud) reviews before merge to `main`
- Always `git pull` before acquiring lock

### File ownership (soft zones)

When both agents might touch adjacent areas, split by phase in handoff:

| Zone | Preferred agent |
|------|-----------------|
| `/docs/*` | Either; Cloud chief owns coordination docs |
| Backend `/backend/*` | OpenCloud for local run; either for code |
| Frontend `/frontend/*` | Either |
| Infra / deploy on Mac Mini | OpenCloud |
| GitHub PRs / branch hygiene | Cursor Cloud |

If unsure → note in handoff and wait for Alex or chief to assign.

### Parallel work forbidden

- Do **not** edit code while the other agent holds the lock
- Do **not** start a new session without checking `CURRENT_TASK.md`
- Alex should not run both agents on the same task simultaneously

---

## Communication Channels

| Channel | Use for |
|---------|---------|
| `docs/CURRENT_TASK.md` | Lock, active task, handoff (required) |
| `docs/DECISIONS_LOG.md` | Architectural / product decisions |
| `docs/BACKLOG.md` | Deferred ideas |
| Git commits | What changed |
| PR descriptions | Review context for Alex |

---

## Agent IDs

Use exactly these values in `lock_holder`:

- `cursor-cloud` — Cursor Cloud Agent (chief)
- `opencloud` — OpenCloud Agent (Mac Mini / local)
- `none` — no active agent

---

## Chief Responsibilities (Cursor Cloud)

- Maintain this protocol and `CURRENT_TASK.md` format
- Resolve conflicting handoffs
- Open/update PRs after substantive work
- Keep `DECISIONS_LOG.md` updated on major decisions
- Assign next task in handoff when direction is clear

---

## OpenCloud Agent: First Message Checklist

On every session start, read this file and run:

```
1. git pull origin main
2. cat docs/CURRENT_TASK.md
3. If lock_holder == none → acquire lock → push
4. If lock_holder == cursor-cloud → wait, read Last handoff
5. Follow ASK → PLAN → BUILD (no code without Alex OK on major items)
```

---

*Established: 2026-06-11 — Cursor Cloud Agent (chief)*
