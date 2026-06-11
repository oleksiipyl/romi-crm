# CURRENT TASK — Active Assignments

> **Managed by: Senya (OpenClaw Tech Lead)**
> Last updated: 2026-06-11 22:40 PDT
> Last Handoff: `Senya ACK cursor-cloud ✅`

---

## Active Assignments

| Agent | Task | Files OK | Files OFF limits | Status | Branch |
|-------|------|----------|------------------|--------|--------|
| cursor-cloud | **Redesign calculator UI** — rebuild `frontend/index.html` for romi-estimate with improved UX: compact layout, better mobile experience, radio buttons for options, cleaner design. Read DEVELOPMENT_STANDARDS.md first. Visual QA at 375/768/1440px. | `frontend/*` | `backend/*` `docs/*` | **assigned** | cursor/ui-redesign-v2 |

---

## Task Details for cursor-cloud

### Task: Redesign Calculator UI (romi-estimate)

**Repo:** https://github.com/oleksiipyl/romi-estimate

**Goal:** The current calculator works but needs UX improvements.

**What to fix:**
1. Category selection — horizontal scrollable pill row (already OK)
2. Product cards — 2-column grid (already OK, keep)
3. Options fields — make sure pills show properly on mobile, no overflow
4. Dimensions — compact 2-column layout
5. Result — bigger price display, better breakdown table
6. Overall feel — cleaner, more professional, Apple-like

**Design specs:**
- White background, #2563EB blue, Inter/system font
- Mobile 375px first
- No hardcoded pixel widths (use w-full, max-w-*)
- Tailwind CSS CDN only
- Single HTML file

**Definition of Done:**
- [ ] File written to frontend/index.html
- [ ] Works on 375px mobile (no horizontal scroll)
- [ ] Works on 1440px desktop
- [ ] All 5 steps visible and functional
- [ ] Auto-calculate on change (400ms debounce)
- [ ] Similar jobs panel shows
- [ ] Committed and pushed to branch cursor/ui-redesign-v2

**Resources:**
- Backend API: http://localhost:8001
- Current file: romi-estimate/frontend/index.html
- Standards: romi-crm/docs/DEVELOPMENT_STANDARDS.md

---

## Protocol

```
SENYA ASSIGNS → cursor-cloud reads CURRENT_TASK.md
cursor-cloud: git checkout -b cursor/ui-redesign-v2
cursor-cloud: WORK on Files OK only
cursor-cloud: commit + push
cursor-cloud: update this file: Status = DONE + PR link
SENYA: reviews + merges
```

---

## Completed Tasks

*(empty — first task)*

---

*Senya (OpenClaw) — Tech Lead*
*Protocol: SYNC → OPEN → WORK → CLOSE*
