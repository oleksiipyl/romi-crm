# CURRENT TASK — Assignments & Handoff

> **Read before every session.** Protocol: `docs/AGENT_COORDINATION.md` (when merged)  
> **Only Senya (OpenClaw) edits Active Assignments.**

---

## Coordinator (single head)

```yaml
coordinator: openclaw    # Senya — единственный Tech Lead
updated_by: openclaw
updated_at: 2026-06-11
```

---

## Active Assignments

> Параллельная работа **разрешена**, если Сеня назначил разным агентам **разные** задачи и **разные** файлы.

| Agent | Task | Files OK | Files OFF limits | Status | Branch |
|-------|------|----------|------------------|--------|--------|
| cursor-cloud (CRM) | Review AGENTS.md and DEVELOPMENT_STANDARDS.md — ensure they reflect current team structure (13 agents). Add any missing agent descriptions. | `docs/AGENTS.md` `docs/DEVELOPMENT_STANDARDS.md` | `backend/*` `frontend/*` | in-progress | `cursor/agents-review` |

**Status values:** `assigned` → `in_progress` → `done` | `blocked`

---

## Rules (both agents)

1. **Нет строки с твоим agent ID** → не работай, жди Сеню.
2. **Есть назначение** → SYNC → OPEN → работа только в Files OK → CLOSE.
3. **Не трогай** Files OFF limits и чужие Files OK.
4. **Не добавляй себе задачу сам** — только Сеня правит таблицу выше.

---

## Last Handoff

| Field | Value |
|-------|-------|
| **From** | openclaw (Senya) |
| **Completed** | 2026-06-11 — Assigned agents review task to cursor-cloud (CRM) |
| **Next** | cursor-cloud: review AGENTS.md + DEVELOPMENT_STANDARDS.md on `cursor/agents-review` |
| **Notes** | Task registered by Senya via Alex |

---

## Handoff Log (newest first)

### 2026-06-11 — openclaw (Senya)
- Assigned cursor-cloud (CRM): review AGENTS.md + DEVELOPMENT_STANDARDS.md (13 agents)
- Branch: `cursor/agents-review`

---

*Only Senya (openclaw) may edit Active Assignments.*
