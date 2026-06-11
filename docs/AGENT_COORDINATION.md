# ROMI CRM — Agent Coordination Protocol

> How **Senya (OpenClaw)** and **Cursor Cloud** work together without conflicts.
> GitHub repo is the single source of truth for status and handoffs.

---

## Identity

```
OpenClaw  =  Senya   (Tech Lead, orchestrator, Alex's main contact)
Cursor Cloud  =  Senya's remote repo agent (GitHub, PRs, cloud builds)
```

**Senya** is one person/role. He runs locally via **OpenClaw** on Mac Mini.
**Cursor Cloud** is Senya's hands in the cloud — executes repo work when Senya assigns it.

Alex talks to **Senya (OpenClaw)**. Senya coordinates Cursor Cloud through git handoffs.

---

## Two Agents, One Repo

```
                    ┌─────────────────┐
                    │   ALEX (Human)  │
                    │  Product Owner  │
                    └────────┬────────┘
                             │ Russian, ASK→PLAN→BUILD
                    ┌────────▼────────┐
                    │  SENYA          │
                    │  (OpenClaw)     │
                    │  Tech Lead      │
                    └───┬─────────┬───┘
                        │         │
              Telegram  │         │  git handoff
              Mac Mini  │         │
                        │    ┌────▼────────────┐
                        │    │  CURSOR CLOUD   │
                        │    │  (repo agent)   │
                        │    │  GitHub + PRs   │
                        │    └────────┬────────┘
                        │             │
                        └─────────────┴──────────────►
                             github.com/oleksiipyl/romi-crm
                             docs/CURRENT_TASK.md  ← lock + handoff
```

| Agent ID | Who | Platform | Role |
|----------|-----|----------|------|
| `openclaw` | **Senya** | [openclaw.ai](https://openclaw.ai) / Mac Mini | Tech Lead: plans, decides, talks to Alex, local dev, deploy |
| `cursor-cloud` | Senya's repo agent | Cursor Cloud | GitHub, PRs, cloud implementation — works when Senya assigns |

**Rule: only ONE agent works at a time.** The other waits or reads only.

### Cross-repo (ROMI Estimate)

`romi-estimate` is a **separate repo** with its own `docs/CURRENT_TASK.md`.
CRM and Estimate locks are independent — parallel work OK across repos.
Same SYNC → OPEN → CLOSE protocol — see `docs/ROMI_ESTIMATE_COORDINATION.md`.

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
lock_holder: cursor-cloud   # or openclaw
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
- Work on feature branches: `cursor/<name>-68b2` (Cloud) or `openclaw/<name>` (OpenClaw)
- Merge via PR only; Senya (OpenClaw) approves before merge to `main`
- Always `git pull` before acquiring lock

### File ownership (soft zones)

When both agents might touch adjacent areas, split by phase in handoff:

| Zone | Preferred agent |
|------|-----------------|
| `/docs/*` | Senya (OpenClaw) owns decisions; either can edit with lock |
| Backend `/backend/*` | Senya (OpenClaw) for local run; either for code |
| Frontend `/frontend/*` | Either |
| Infra / deploy on Mac Mini | Senya (OpenClaw) |
| GitHub PRs / branch hygiene | Cursor Cloud (on Senya's assignment) |

If unsure → note in handoff and wait for Alex or Senya to assign.

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

- `openclaw` — **Senya** (Tech Lead, OpenClaw / Mac Mini)
- `cursor-cloud` — Senya's Cursor Cloud repo agent
- `none` — no active agent

---

## Senya (OpenClaw) Responsibilities

- Main contact with Alex (Russian)
- ASK → PLAN → BUILD — plans before code
- Architectural decisions → `DECISIONS_LOG.md`
- Assign tasks to Cursor Cloud via handoff in `CURRENT_TASK.md`
- Approve PRs before merge to `main`
- Local dev, Mac Mini deploy, Telegram

---

## Cursor Cloud Responsibilities

- Execute repo tasks assigned by Senya in handoff
- Open/update PRs, push branches
- Never start major work without handoff from Senya (or Alex OK)
- Report completion back via handoff → release lock

---

## Session Checklist (both agents)

```
1. git pull origin main
2. cat docs/CURRENT_TASK.md
3. If lock_holder != your ID and != none → STOP, read handoff
4. If lock_holder == none → acquire lock → push
5. Read ARCHITECTURE.md + AGENTS.md (Senya section if openclaw)
6. Work → commit → push → handoff → release lock
```

**OpenClaw (Senya) additionally:** communicate with Alex before major BUILD phase.

---

*Established: 2026-06-11 — Senya + Cursor Cloud*
