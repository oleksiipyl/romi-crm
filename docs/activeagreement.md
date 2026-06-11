# Active Agreement — Agent Coordination

> Last updated: 2026-06-11 01:50 PDT
> Protocol version: 1.0

---

## Agent Registry

| Agent | Role | Status | Channel |
|-------|------|--------|---------|
| **senya** (OpenClaw) | Tech Lead / Orchestrator | 🟢 ONLINE | Telegram → Alex |
| **cursor-cloud** | Frontend / Full-stack Dev | 🟡 STANDBY | GitHub PR / Alex prompt |

---

## How to reach each agent

### Senya (OpenClaw)
- Senya видит этот файл при каждом старте сессии
- Senya управляет через CURRENT_TASK.md
- Чтобы Senya назначил задачу cursor-cloud → обнови CURRENT_TASK.md и напиши Alex

### Cursor Cloud
- Не polling GitHub 24/7 — нужен триггер
- Триггер 1: Alex пишет Cloud Agent в Cursor
- Триггер 2: @cursor в GitHub PR/Issue  
- Триггер 3: Cursor API (когда настроим)
- Читает задачу из CURRENT_TASK.md при запуске

---

## Current Active Task

→ See `CURRENT_TASK.md`

**Assigned to:** cursor-cloud  
**Task:** Redesign calculator UI (romi-estimate)  
**Branch:** cursor/ui-redesign-v2  
**Status:** assigned

---

## Senya → Cursor-Cloud Protocol

```
1. Senya обновляет CURRENT_TASK.md
2. Senya пушит в main
3. Alex запускает Cursor Cloud Agent: "SYNC → OPEN"
4. cursor-cloud читает задачу → работает → пушит PR
5. Senya/Alex ревьюит → merge
```

---

## Notes for Senya

- Cursor Cloud API key нужен для автоматического триггера
- Когда Alex даст API key → добавить в OpenClaw → Senya сможет будить cursor-cloud сам
- До тех пор: Alex = мост между Senya и Cursor Cloud

---

*Senya (OpenClaw) — ONLINE*  
*Beacon written: 2026-06-11T08:50:00Z*
