# ROMI Estimate — Agent Coordination Protocol

> Same rules as ROMI CRM. **Senya = single Tech Lead.**  
> Repo: `github.com/oleksiipyl/romi-estimate`

---

## One head (same Senya)

```
Alex  →  Senya (OpenClaw)  →  assigns  →  Cursor Cloud Estimate / himself
```

- Only Senya assigns tasks in `docs/CURRENT_TASK.md`
- Parallel with ROMI CRM OK — different repos, Senya coordinates both boards

---

## Project

| Item | Value |
|------|-------|
| Product | ROMI Estimate — field glass calculator |
| Stack | FastAPI + SQLite + plain HTML (mobile-first) |
| Pricing | Port from `bot_correct.py` |
| Spec | `ESTIMATE_APP_IDEA.md` |

---

## SYNC → OPEN → CLOSE

Same as CRM — see `romi-crm/docs/AGENT_COORDINATION.md`.

1. **SYNC** — `git pull`, read `docs/CURRENT_TASK.md`
2. **No assignment for you?** — STOP, wait for Senya
3. **OPEN** — your status `assigned` → `in_progress`, push
4. **WORK** — only **Files OK** from your assignment row
5. **CLOSE** — status → `done`, handoff, push

---

## Parallel examples (Senya decides)

| CRM (romi-crm) | Estimate (romi-estimate) | OK? |
|----------------|--------------------------|-----|
| Senya: backend | Cursor: estimate UI | ✅ |
| Both on same repo, same files | — | ❌ |

---

## Bootstrap (first time)

1. Copy this file → `docs/AGENT_COORDINATION.md`
2. Create `docs/CURRENT_TASK.md` (assignment board, empty)
3. Copy `ESTIMATE_APP_IDEA.md` into `/docs/`
4. Wait for Senya to fill Active Assignments

---

*Mirror of ROMI CRM v2 — Senya assigns, parallel OK*
