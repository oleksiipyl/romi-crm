# AI Lead Responder — архитектура (Yelp → Zapier → Railway → GHL)

Единый источник правды по структуре. Если что-то непонятно — смотри сюда.

---

## Карта (4 слоя)

```
YELP            канал клиента (лиды + сообщения)
  │  событие
  ▼
ZAPIER          транспорт: 2 Zap, БЕЗ бизнес-логики
  │  POST webhook (JSON)
  ▼
RAILWAY         мозг + память (FastAPI)
  ├── PostgreSQL    история диалога по lead_id
  ├── OpenAI        генерация текста (GPT-4o)
  └── GHL CRM       поиск/создание контакта, передача менеджеру
  │  ответ: should_post + messages[]
  ▼
ZAPIER → YELP   Create Message (если should_post)
```

**Хребет системы — `lead_id`.** Один и тот же ID треда Yelp во всех слоях:
`Yelp lead_id` = `PostgreSQL.channel_thread_id` = `GHL custom field yelp_lead_id`.
Рвётся `lead_id` → теряется память и персона. Это причина большинства проблем.

---

## Кто за что отвечает

| Слой | Роль | Принимает | Отдаёт |
|------|------|-----------|--------|
| Yelp | Канал | — | событие New Lead / New Message |
| Zapier | Транспорт | событие Yelp | POST на Railway; постит ответ |
| Railway | Мозг: память, AI, решение | JSON webhook | `should_post`, `messages[]`, `state` |
| PostgreSQL | Память | запись по `lead_id` | история |
| OpenAI | Текст | промпт + история | ответ |
| GHL | CRM/продажи | контакт, телефон, сделка | найден ли контакт |

---

## Контракт ответа (главное упрощение)

Backend решает, постить или нет. Zapier проверяет **одно** поле.

```jsonc
{
  "should_post": true,            // единственный фильтр в Zapier
  "messages": ["MSG1", "MSG2"],   // постить по порядку
  "state": "offer",
  "conversation_id": "uuid"
}
```

`should_post = false`, когда: пустой ответ, дубль (`message_id`/текст), `state=human_active`,
сообщение от `BUSINESS`. Тогда Zapier не делает ничего.

---

## Два потока

**A — Новый лид (Zap A):**
```
Yelp New Lead → Zapier POST(trigger=new_lead, lead_id, name, project, zip)
→ Railway: создать conversation + контакт в GHL (early)
→ GPT-4o: 2 сообщения (MSG1 приветствие+телефон, MSG2 цена)
→ should_post=true, messages=[MSG1, MSG2]
→ Zapier: Filter should_post → Msg → Delay → Msg → Yelp
```

**B — Ответ клиента (Zap B):**
```
Yelp New Message → Zapier POST(lead_id, message, user_type, message_id)
→ Railway: найти conversation (память)
   ├ телефон совпал с GHL in-progress → human_takeover (should_post=false)
   └ иначе → GPT-4o с историей → should_post=true, messages=[reply]
→ Zapier: Filter should_post → Msg → Yelp
```

---

## GHL — 3 точки синхронизации

| Когда | Действие |
|-------|----------|
| Лид пришёл | Найти/создать контакт, tag `yelp`, записать `lead_id` |
| Телефон получен | Обновить телефон, создать opportunity, передать менеджеру + уведомить |
| Существующий клиент (по ТЕЛЕФОНУ) | human_takeover + заметка, AI молчит |

**Передача менеджеру — только по телефону (strong).** Совпадение по имени (weak,
«Robert N.») → только уведомить менеджера заметкой, **AI продолжает работать**.
Имена Yelp слишком часто совпадают, чтобы по ним глушить AI.

---

## Когда AI постит, когда нет

| Ситуация | should_post | messages |
|----------|-------------|----------|
| Новый лид | true | [MSG1, MSG2] |
| Follow-up, AI активен | true | [reply] |
| Дубль (`message_id`/текст ≤60с) | false | [] |
| `user_type = BUSINESS` | false | [] |
| `state = human_active` (передан менеджеру) | false | [] |
| Совпадение по телефону (существующий) | false | [] |

---

## Принципы «правильной» структуры

1. **`lead_id` един везде** (Zapier ↔ БД ↔ GHL). Главное.
2. **Один мозг — Railway.** Zapier только транспорт, ноль логики.
3. **Backend решает постинг** (`should_post`), Zapier подчиняется. Один фильтр.
4. **Takeover только по телефону.** Имя — лишь уведомление.
5. **Идемпотентность** по `message_id`; вебхук всегда HTTP 200.
6. **GHL — источник правды по продажам**, не дублировать логику в Zapier.
