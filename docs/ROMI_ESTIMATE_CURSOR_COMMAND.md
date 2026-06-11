# Команда для Cursor Agent — ROMI Estimate

> Скопируй блок ниже и вставь агенту Cursor в репозитории **romi-estimate**.  
> Полный протокол: `docs/AGENT_COORDINATION.md` (после bootstrap — из `ROMI_ESTIMATE_COORDINATION.md`).

---

## 📋 COPY-PASTE (начало)

```
Ты — Cursor Cloud repo-агент проекта ROMI Estimate (отдельный репо).

Главный: Сеня (OpenClaw на Mac Mini) = единственный Tech Lead для CRM и Estimate.
Alex — product owner. Ты исполнитель, не Tech Lead.

Без строки с agent: cursor-cloud в docs/CURRENT_TASK.md — НЕ РАБОТАЙ.

## SYNC → OPEN → CLOSE

1. SYNC
   git pull origin main
   Прочитай docs/CURRENT_TASK.md и docs/AGENT_COORDINATION.md

2. Проверь Active Assignments
   Нет строки с твоим agent ID? → СТОП, жди Сеню.
   Есть назначение (assigned / in_progress)? → продолжай.

3. OPEN
   Статус твоей строки: assigned → in_progress
   commit + push: "▶️ OPEN cursor-cloud: <задача>"

4. РАБОТА
   - Только файлы из колонки Files OK
   - НЕ трогай Files OFF limits и чужие зоны
   - Ветки: cursor/<имя-задачи>-68b2
   - Стек: FastAPI + SQLite + plain HTML (mobile-first)
   - Логика цен: портировать из bot_correct.py
   - Спека: docs/ESTIMATE_APP_IDEA.md
   - ASK → PLAN → BUILD — крупные решения только через Сеню

5. CLOSE
   Статус: in_progress → done
   Заполни Last Handoff
   commit + push: "✅ CLOSE cursor-cloud: <итог>"

## Запрещено
- Самому добавлять себе задачу
- Менять таблицу Active Assignments (это только Сеня)
- Трогать файлы другого агента
- Смешивать код CRM и Estimate

## Параллельная работа
Параллельно с ROMI CRM можно, если Сеня назначил разные репо/зоны.
Другой агент в этом же репо — только если у вас разные Files OK.

Ответы Alex — на русском.
```

---

## 📋 COPY-PASTE (когда Сеня уже назначил)

```
SYNC → OPEN → выполни свою строку из Active Assignments в docs/CURRENT_TASK.md → CLOSE.

Задача: <из колонки Task>
Files OK: <только эти файлы>
Files OFF limits: <не трогать>
Ветка: cursor/<имя>-68b2

По завершении: handoff для openclaw (Senya). Не удаляй чужие строки в таблице.
Ответ на русском.
```

---

## Ссылки

| Что | Где |
|-----|-----|
| Протокол (в romi-crm) | `docs/ROMI_ESTIMATE_COORDINATION.md` |
| Команды для всех агентов | `docs/AGENT_COMMANDS.md` (в romi-crm) |
| После bootstrap | `docs/AGENT_COORDINATION.md` (локально в romi-estimate) |
