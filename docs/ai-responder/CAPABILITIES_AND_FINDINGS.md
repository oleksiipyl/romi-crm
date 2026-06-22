# AI Lead Responder — разбор возможностей и результат

Глубокий разбор: что система **умеет**, что **принимает/отдаёт**, какие баги
найдены, что **исправлено** и что осталось риском. Для Alex.

---

## 1. Что система умеет (capabilities)

| Возможность | Где в коде | Статус |
|-------------|-----------|--------|
| Приём вебхука Yelp от Zapier | `api/v1/ai_responder.py` | работает |
| Нормализация полей Yelp/Zapier | `services/ingest.py: normalize_yelp_payload` | + добавлены Yelp-имена полей |
| Память диалога по `lead_id` (PostgreSQL) | `ingest.py: get_or_create_conversation` | работает |
| Классификация события (new_lead / message / phone) | `ingest.py: resolve_yelp_event_kind` | работает |
| Дедуп по `message_id` и по тексту (60 сек) | `ingest.py: _should_skip_duplicate_message` | работает |
| Анти-петля: игнор `user_type=BUSINESS` | `ai_responder.py` | работает |
| Первый ответ из 2 сообщений (MSG1+MSG2) | `ai_brain.py: parse_two_message_reply` | работает |
| Контекстные follow-up через GPT-4o + история из БД | `ai_brain.py: generate_reply` | работает |
| Персона (Robert/Olivia/Al), фикс на тред | `services/personas.py` | работает |
| Инструменты: get_price, collect_phone, human_takeover, book_estimate, trigger_callback, escalate | `services/tools.py` | get_price/collect_phone/takeover активны; callback/book — заглушки Phase 1/2 |
| Расчёт цены по каталогу + ZIP | `services/kb.py`, `tools.py: get_price` | работает |
| Сбор телефона → синк в GHL → human takeover | `tools.py: collect_phone`, `ghl.py: upsert_yelp_lead` | работает |
| Раннее создание контакта в GHL на первом лиде | `ghl.py: ensure_early_yelp_contact` | работает |
| Поиск существующего контакта (phone strong / name weak) | `services/contact_check.py`, `ghl.py` | **исправлен краш** |
| Передача менеджеру при совпадении контакта | `services/takeover_funnel.py` | работает (см. риск №2) |
| Таймерные follow-up (24/48/48ч), 3 попытки, abandon | `services/state_machine.py` | логика есть; запуск по расписанию — отдельно |
| Fallback-ответы без OpenAI / при ошибке | `ai_brain.py: _fallback_reply` | работает |
| Twilio SMS канал (заготовка) | `ai_responder.py: twilio_sms_webhook` | Phase 1 stub |
| HCP поиск клиента по телефону | `services/hcp.py` | опционально (если ключ задан) |

---

## 2. Контракт I/O (что принимает / что отдаёт)

### Принимает: `POST /api/v1/ai-responder/webhooks/zapier/yelp`

```jsonc
{
  "lead_id": "iGp3_N6LD_eUJnhyShoz0g",   // ОБЯЗАТЕЛЬНО — ключ треда = память
  "trigger": "new_lead",                  // new_lead для Zap A; пусто/др. для Zap B
  "consumer_name": "Robert N.",
  "message": "Could you provide a quote?",// или consumer_message
  "project_description": "shower door",    // или "Project Additional Info"
  "service_type": "...",                   // или "Project Job Names"
  "zip_code": "90211",                     // или "Location Postal Code"
  "user_type": "CONSUMER",                 // BUSINESS → игнор
  "message_id": "yelp_msg_123"             // дедуп
}
```

Заголовок `X-Webhook-Secret` — если задан `ZAPIER_WEBHOOK_SECRET` (иначе не проверяется).

### Отдаёт

```jsonc
{
  "status": "ok",
  "conversation_id": "uuid",
  "reply_text": "текст в Yelp",
  "reply_text_2": "второе сообщение (только new_lead)",
  "state": "offer | qualify | human_active | duplicate | skipped",
  "event_type": "new_lead | ''",
  "fallback": false,                       // true = ответ без OpenAI
  "tools_called": ["get_price"]
}
```

**Правила для Zapier:**
- `state=human_active` или пустой `reply_text` → **не постить** в Yelp (Filter).
- `state=duplicate` / `skipped` → ничего не делать.
- Zap A: постит `reply_text`, затем Delay, затем `reply_text_2`.
- Zap B: постит только `reply_text`.

---

## 3. Найденные баги (с доказательствами)

### БАГ №1 (КРИТ, исправлен): 500 на follow-up при имени из CRM

**Симптом:** new_lead → 200, а follow-up на тот же `lead_id` → **HTTP 500**.

**Доказательство на проде** (`web-production-3b1a9`):
- `consumer_name="Alex"` → follow-up **500** каждый раз.
- `consumer_name="Jennifer Martinez"` / `"Robert N."` → follow-up **200**.

**Причина:** на 2-м сообщении backend ищет контакт в GHL по имени.
GHL возвращает контакты с `firstName: null`. Старый код:

```python
contact.get("name") or contact.get("firstName", "") + " " + contact.get("lastName", "")
```

`None + " "` → `TypeError` → исключение до ответа AI → 500. Имя «Alex» (владелец)
есть в их GHL с пустым `firstName`, поэтому падало именно на нём.

**E2E-доказательство:** `tests/test_e2e_followup_ghl_crash.py` гоняет полный
ASGI-стек с фейковым GHL, отдающим `firstName:null`. На старом коде — 500
(тест падает), на новом — 200 (тест проходит).

### БАГ №2 (РИСК, не менял без OK): «тихий AI» из-за совпадения по имени

**Где:** `takeover_funnel.py: evaluate_post_first_reply` — после первого ответа
делает `human_takeover` при **любом** совпадении контакта, включая **weak**
(только по имени). Закреплено тестом `test_funnel_weak_match_takeover_after_first`.

**Чем грозит:** имена Yelp короткие («Robert N.»). Если такое имя совпадёт с
контактом в GHL (а матч нестрогий: `target in contact_name`), AI отправит первое
сообщение и **замолчит навсегда** — это и есть жалоба «одно сообщение, дальше тишина».

**Рекомендация (нужен OK Alex):** делать takeover **только на strong** (совпадение
по телефону). Weak (по имени) → уведомить менеджера заметкой, но **AI продолжает**.
Правка локальная: 2 условия в `evaluate_post_first_reply` и `evaluate_inbound_contact`.

### Прочее (проверено — НЕ воспроизводится на проде сейчас)
- **Повтор приветствия на 2-м сообщении** — на проде follow-up отвечает «Totally
  get it!…» без ре-приветствия. Причина прошлых жалоб — другой `lead_id` между
  Zap A и Zap B (тред не связался) либо как раз 500.
- **Robert → Olivia** — персона стабильна в рамках одного `lead_id`. Смена = новый
  тред (потеря `lead_id`).
- **Шаблон $349/$625** — был из-за того, что Zap A не присылал описание. Маппинг
  Yelp-полей добавлен; нужно проверить настройку Zap A (см. §5).

---

## 4. Что исправлено в этом PR

1. **ghl.py** — null-safe сбор имени (`_contact_display_name`), фильтр не-dict
   в списках contacts/opportunities, `_request` всегда возвращает dict.
2. **contact_check.py** — `try/except` вокруг GHL-поиска по телефону и имени.
3. **takeover_funnel.py** — на follow-up ловим любую ошибку GHL и продолжаем
   (defer), не роняя вебхук.
4. **ingest.py** — маппинг Yelp Zapier-полей (`Project Additional Info`,
   `Project Job Names`, `Location Postal Code`); описание из new_lead кладётся
   в `metadata.project_description`.
5. **Тесты** — `test_ghl_parsing.py`, `test_e2e_followup_ghl_crash.py`,
   нормализация Yelp-полей. Итого **88 passed**.
6. **Доки** — `FLOW.md` (схема потока) + этот разбор.

---

## 5. Чек-лист настройки Zapier (чтобы результат был стабильным)

**Zap A — New Lead (5 шагов):**
1. Trigger: Yelp New Lead
2. POST на вебхук: `trigger=new_lead`, `lead_id`, `consumer_name`,
   `project_description` (= Yelp «Project Additional Info»), `zip_code`
3. Create Message (Yelp) ← `reply_text`
4. Delay 30–60 сек
5. Create Message (Yelp) ← `reply_text_2`

**Zap B — New Consumer Message (4 шага):**
1. Trigger: Yelp New Consumer Message
2. POST: `lead_id`, `consumer_name`, `message`, `user_type=CONSUMER`, `message_id`
3. Filter: `reply_text` не пустой **И** `state` ≠ `human_active` **И** `status` = `ok`
4. Create Message (Yelp) ← `reply_text`

> Главное: `lead_id` в обоих Zap должен быть **один и тот же** ID треда Yelp —
> иначе память не свяжется и будет повтор приветствия.

---

## 6. Результат

- Прод-баг 500 на follow-up — **устранён и доказан E2E** (полный стек + реальный
  парсер GHL).
- Память, дедуп, 2-сообщенческий первый ответ, персоны, расчёт цены — **работают**.
- Поток Yelp → БД → ИИ → Yelp **разобран** (`FLOW.md`).
- Риск «тихого AI» по совпадению имени — **локализован**, ждёт OK на правку.

**Деплой:** влить ветку в `main` → Railway пересоберёт → follow-up с любым именем
(включая «Alex») снова возвращает 200.
