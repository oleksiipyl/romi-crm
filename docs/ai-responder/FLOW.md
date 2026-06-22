# AI Lead Responder — поток данных (Yelp → БД → ИИ → Yelp)

Короткая схема для отладки Zapier и Yelp-тредов.

## Цепочка

```
Yelp
  → Zapier (триггер)
  → POST /api/v1/ai-responder/webhooks/zapier/yelp
  → ingest.py (нормализация + PostgreSQL)
  → [follow-up] takeover_funnel.py (GHL lookup)
  → ai_brain.py (GPT-4o + tools)
  → JSON ответ → Zapier Create Message → Yelp
```

**Ключ памяти:** `lead_id` из Yelp = `ai_conversations.channel_thread_id`.  
История чата **не** приходит из Zapier — backend читает `ai_messages` по этому `lead_id`.

---

## Что принимает webhook (POST body)

| Поле Zapier | Зачем | Куда в БД |
|-------------|-------|-----------|
| `lead_id` | ID треда Yelp | `channel_thread_id` |
| `trigger` | `new_lead` или пусто | тип события |
| `consumer_name` | Имя клиента | `metadata.lead_name` |
| `message` / `consumer_message` | Текст сообщения | `ai_messages` (inbound) |
| `project_description` / `Project Additional Info` | Описание работы | `metadata.project_description` |
| `Project Job Names` | Тип работы | `metadata.service_type` |
| `zip_code` / `Location Postal Code` | ZIP | `zip_code` |
| `user_type` | `CONSUMER` / `BUSINESS` | `BUSINESS` → skip (анти-петля) |
| `message_id` | ID сообщения Yelp | dedup по `external_id` |

### Два Zap

| Zap | Триггер | Обязательные поля POST |
|-----|---------|------------------------|
| **A** New Lead | новый лид | `trigger=new_lead`, `lead_id`, `consumer_name`, описание/ZIP |
| **B** Consumer Message | ответ клиента | `lead_id`, `message`, `user_type=CONSUMER`, `message_id` |

---

## Что делает backend по шагам

### 1. ingest.py

1. `normalize_yelp_payload()` — единый формат полей (в т.ч. Yelp-имена из Zapier).
2. `get_or_create_conversation()` — найти или создать `ai_conversations` по `lead_id`.
3. Классификация: `new_lead` | `message` | `phone` | `noop`.
4. Для `message` — запись в `ai_messages` (direction=inbound, sender=lead).
5. Dedup: тот же `message_id` или тот же текст за 60 сек → `state=duplicate`, пустой ответ.

### 2. GHL (только follow-up, не первый ответ)

- **Первый ответ (new_lead):** AI сразу, GHL lookup в фоне (`evaluate_post_first_reply`).
- **2+ сообщение:** `evaluate_inbound_contact` — ищет контакт в GHL по телефону/имени.
  - Найден **in-progress** → `human_takeover`, `reply_text=""`, Zapier не постит.
  - Иначе → AI отвечает.

### 3. ai_brain.py

- Загружает историю из `ai_messages` (все text-сообщения по `conversation_id`).
- **New lead:** 2 сообщения — `reply_text` (MSG1) + `reply_text_2` (MSG2).
- **Follow-up:** одно `reply_text`, контекст из БД + новый inbound.
- Persona (Robert/Olivia/Al) фиксируется в `metadata.agent_name` при создании треда.
- Tools: `get_price`, `collect_phone`, `human_takeover`.

### 4. Ответ webhook (что видит Zapier)

```json
{
  "status": "ok",
  "conversation_id": "uuid",
  "reply_text": "текст для Yelp",
  "reply_text_2": "второе сообщение (только new lead)",
  "state": "offer | human_active | duplicate | skipped",
  "event_type": "new_lead | ...",
  "fallback": false,
  "tools_called": ["get_price"]
}
```

**Zap A:** Create Message `reply_text` → Delay → Create Message `reply_text_2`.  
**Zap B:** Filter (`state != human_active`, `status=ok`, `reply_text` не пустой) → Create Message `reply_text`.

---

## Таблицы PostgreSQL

| Таблица | Роль |
|---------|------|
| `ai_conversations` | Один тред = один Yelp `lead_id`; state, persona, GHL ids |
| `ai_messages` | Вся переписка: inbound (клиент), outbound (AI), tool_call/result |
| `lead_channels` | Связь lead ↔ внешний id (Yelp) |

---

## Типичные баги

| Симптом | Причина |
|---------|---------|
| Шаблон $349/$625 без деталей | Zap A не шлёт `project_description` / Yelp fields |
| Повтор «Hey Robert…» на 2-м сообщении | Другой `lead_id` или Zap A не попал в webhook |
| Robert → Olivia | Новый `lead_id` = новая conversation |
| 500 на follow-up | GHL lookup падал (исправлено: null-safe парсинг имён) |
| Пустой ответ при жёлтом Filter | `state=human_active` — AI передал менеджеру, постить не надо |

---

## Smoke test (prod)

```bash
LEAD="test_$(date +%s)"
# Zap A
curl -X POST "$URL/api/v1/ai-responder/webhooks/zapier/yelp" \
  -H "Content-Type: application/json" \
  -d "{\"trigger\":\"new_lead\",\"lead_id\":\"$LEAD\",\"consumer_name\":\"Test\",\"project_description\":\"window repair\",\"zip_code\":\"90001\"}"

# Zap B
curl -X POST "$URL/api/v1/ai-responder/webhooks/zapier/yelp" \
  -H "Content-Type: application/json" \
  -d "{\"lead_id\":\"$LEAD\",\"message\":\"quote please?\",\"user_type\":\"CONSUMER\",\"message_id\":\"m1\"}"
```

Оба запроса должны вернуть **HTTP 200**.
