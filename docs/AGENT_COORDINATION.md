# ROMI CRM — Agent Coordination Protocol

> **Senya is the single Tech Lead.** He decides who does what.  
> Parallel work is **allowed** when Senya assigns different tasks to different agents.

---

## One head

```
Alex  →  Senya (OpenClaw)  →  assigns  →  Cursor Cloud / himself
         ═══════════════
         единственный Tech Lead
```

- **OpenClaw = Senya** — orchestrator, architect, Alex's contact (Russian)
- **Cursor Cloud** — repo agent; works **only on tasks Senya assigned** in `docs/CURRENT_TASK.md`
- **No agent starts work without Senya's assignment** — no self-assign
- **No second Tech Lead** — all decisions through Senya

---

## Parallel work (when Senya allows)

Senya **may** run agents in parallel if scopes do not overlap:

| Senya assigns | Agent A | Agent B | OK? |
|---------------|---------|---------|-----|
| Backend schema | `openclaw` → `backend/db/*` | `cursor-cloud` → `frontend/*` | ✅ parallel |
| Same file | both on `backend/auth.py` | — | ❌ Senya must split or sequence |
| No assignment | agent starts anyway | — | ❌ forbidden |

**Conflict rule:** touch only files in your **Files OK** column. Never touch **Files OFF limits** or another agent's **Files OK**.

---

## Assignment board: `docs/CURRENT_TASK.md`

Senya maintains **Active Assignments** table:

| Agent | Task | Files OK | Files OFF limits | Status | Branch |
|-------|------|----------|------------------|--------|--------|

- Only **Senya (openclaw)** edits this table
- Agents may only update **their own Status** and **Handoff** sections

---

## SYNC → OPEN → CLOSE

### SYNC (every session)
```bash
git pull origin main
cat docs/CURRENT_TASK.md
```
- No row for your agent ID? → **STOP**, wait for Senya
- Row exists with `assigned` or `in_progress`? → continue

### OPEN (start your assigned task)
- Set your status: `assigned` → `in_progress`
- Commit: `▶️ OPEN cursor-cloud: <task>` (or `openclaw`)
- Push immediately

### WORK
- Stay inside **Files OK**
- Feature branches: `cursor/<name>-68b2` or `openclaw/<name>`
- ASK → PLAN → BUILD; major changes need Alex OK via Senya

### CLOSE (finish your task)
- Set your status: `in_progress` → `done`
- Fill **Last Handoff** (what done, what's next, PR link)
- Commit: `✅ CLOSE cursor-cloud: <summary>`
- Push immediately
- **Do not** remove other agents' assignments — Senya updates the board

---

## Session flow

```
START
  │
  ├─► SYNC (git pull, read CURRENT_TASK.md)
  │
  ├─► Assigned to me? ──NO──► STOP (wait for Senya)
  │
  YES
  │
  ├─► OPEN (status → in_progress, push)
  ├─► Work in Files OK only
  ├─► CLOSE (status → done, handoff, push)
  │
END
```

---

## Senya (OpenClaw) — Tech Lead duties

- Single head for **ROMI CRM** and **ROMI Estimate** (separate repos, same Senya)
- Talk to Alex (Russian), ASK → PLAN → BUILD
- Write assignments in each repo's `CURRENT_TASK.md`
- Split work so parallel agents don't share files
- Approve PRs before merge to `main`
- Document decisions in `DECISIONS_LOG.md`

---

## Cursor Cloud — repo agent duties

- Execute **only** assigned tasks
- Never self-assign, never change Active Assignments table
- OPEN/CLOSE your row only
- Open/update PRs for your branch
- Report blockers to Senya via handoff

---

## Cross-repo (ROMI Estimate)

| Repo | Assignments file | Coordinator |
|------|------------------|---------------|
| `romi-crm` | `docs/CURRENT_TASK.md` | Senya |
| `romi-estimate` | `docs/CURRENT_TASK.md` | Senya (same person) |

Senya can assign CRM backend to OpenClaw and Estimate UI to Cursor Cloud **at the same time** — different repos, no file conflict.

Protocol mirror: `docs/ROMI_ESTIMATE_COORDINATION.md`  
Copy-paste agent prompts: `docs/AGENT_COMMANDS.md`

---

## Agent IDs

| ID | Who |
|----|-----|
| `openclaw` | Senya (Tech Lead) |
| `cursor-cloud` | Cursor Cloud repo agent |

---

## Git rules

- Never force-push `main`
- Merge via PR only; Senya approves
- Always `git pull` before OPEN

---

*Established: 2026-06-11 — v2: Senya assigns, parallel OK*
