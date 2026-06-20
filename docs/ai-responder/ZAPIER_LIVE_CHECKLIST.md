# AI Lead Responder — Zapier LIVE Checklist

> **Scope:** довести Yelp auto-reply до LIVE. Код не трогать без ошибки из Zapier Task History или smoke test.
> **Прод URL:** `https://web-production-3b1a9.up.railway.app`
> **Webhook:** `POST /api/v1/ai-responder/webhooks/zapier/yelp`

---

## Для Сени (IRON RULE)

```
Задача: LIVE Yelp Lead Responder.
Разрешено: Railway env, Zapier Zaps, E2E тест, smoke test.
Запрещено: новая архитектура, рефакторинг, фичи до LIVE.
Если Task History чистый и smoke test OK → только ops, не код.
```

---

## Шаг 0 — Smoke test (2 мин)

Из корня репо:

```bash
bash backend/scripts/smoke_test_yelp_webhook.sh
```

С секретом (если задан в Railway):

```bash
export ZAPIER_WEBHOOK_SECRET='your-secret'
bash backend/scripts/smoke_test_yelp_webhook.sh
```

Другой хост:

```bash
export BASE_URL='https://web-production-3b1a9.up.railway.app'
bash backend/scripts/smoke_test_yelp_webhook.sh
```

**Ожидание:** все шаги `PASS`, `reply_text` не пустой на шагах 1 и 2.

---

## Шаг 1 — Railway env vars (Alex, ~10 мин)

Railway → сервис backend → Variables:

| Variable | Required | Value / notes |
|----------|----------|---------------|
| `DATABASE_URL` | ✅ | `${{Postgres.DATABASE_URL}}` |
| `OPENAI_API_KEY` | ✅ | OpenAI key |
| `OPENAI_MODEL` | optional | `gpt-4o` |
| `GHL_API_TOKEN` | ✅ для funnel | PIT token с browser UA (см. glass-biz `memory/project-gohighlevel.md`) |
| `GHL_LOCATION_ID` | ✅ | `zaegdQlLTbraKW5EzOKF` |
| `GHL_PIPELINE_ID` | ✅ | `OkNyO0uPN26HD0T8NmM4` |
| `GHL_PIPELINE_STAGE_ID` | ✅ | `d157a032-f0ce-44ca-9408-06f1a30994a7` |
| `GHL_YELP_SOURCE` | ✅ | `YELP` |
| `ZAPIER_WEBHOOK_SECRET` | optional | random string — тогда же в Zapier header |
| `HCP_API_KEY` | optional | phone lookup |
| `APP_ENV` | optional | `production` |

После изменений: redeploy → снова smoke test.

---

## Шаг 2 — Zap A: New Lead (первый ответ)

**Trigger:** Yelp Leads → **New Lead**

**Action 1:** Webhooks by Zapier → **POST**

| Field | Value |
|-------|-------|
| URL | `https://web-production-3b1a9.up.railway.app/api/v1/ai-responder/webhooks/zapier/yelp` |
| Payload type | JSON |
| Header (если secret) | `X-Webhook-Secret: <ZAPIER_WEBHOOK_SECRET>` |

**JSON body (map from trigger):**

```json
{
  "trigger": "new_lead",
  "lead_id": "<Lead ID from trigger>",
  "consumer_name": "<Consumer Name>",
  "phone_number": "<Phone if available>",
  "project_description": "<Project description / survey>",
  "zip_code": "<Zip>",
  "service_type": "<Service type if any>",
  "user_type": "CONSUMER"
}
```

В Zapier: замапить поля из trigger — не оставлять пустой `lead_id`.

**Action 2:** Yelp Leads → **Create Message**

| Field | Map from |
|-------|----------|
| Lead ID | Trigger → Lead ID (не из webhook!) |
| Response Content | Webhook step → `reply_text` |

**Filter (optional):** только если `reply_text` не пустой.

---

## Шаг 3 — Zap B: New Consumer Message (диалог)

**Trigger:** Yelp Leads → **New Consumer Message**  
⚠️ **НЕ** New Business Message — это наши ответы.

**Action 1:** Webhooks POST — same URL и headers как Zap A.

**JSON body:**

```json
{
  "lead_id": "<Lead ID>",
  "consumer_name": "<Consumer Name>",
  "message": "<Message text>",
  "message_id": "<Message ID if available>",
  "user_type": "CONSUMER"
}
```

`trigger` можно не передавать — backend определяет follow-up.

**Action 2:** Create Message — `reply_text` → Response Content.

**Filter:** `reply_text` length > 0.

---

## Шаг 4 — Что НЕ делать

| Mistake | Effect |
|---------|--------|
| Trigger **Business Message** | loop или skip |
| Create Message без `lead_id` | Yelp 400, лид без ответа |
| Map `reply_text` из не того step | пустой ответ в Yelp |
| Secret в Railway, но не в Zapier | HTTP 401 |
| Один Zap только на New Lead | follow-up клиента не отвечается |
| Ждать Yelp Partner API | не нужно для LIVE |

---

## Шаг 5 — Debug: 2 лида не подхватили (D1)

Zapier → Zap → **Task History** → failed run:

| Error | Fix |
|-------|-----|
| `401 Invalid webhook secret` | Sync `ZAPIER_WEBHOOK_SECRET` Railway ↔ Zapier header |
| `reply_text` empty, state `duplicate` | норма — дедуп; проверить не двойной trigger |
| `reply_text` empty, state `skipped` | `user_type` = BUSINESS — исправить trigger |
| `reply_text` empty, `human_takeover` | existing GHL client — AI молчит намеренно |
| Timeout / Zap error | Railway logs; 2-й ответ +4–8s typing — обычно <30s |
| Create Message failed | `lead_id` mapping |
| Webhook 500 | Railway logs + smoke test |

Railway logs:

```bash
railway logs --service <backend-service>
```

---

## Шаг 6 — E2E на реальном лиде (F)

1. Отправить тестовый RAQ на Yelp (или дождаться реального).
2. Zapier Task History: trigger → webhook 200 → Create Message success.
3. Yelp thread: ответ от Robert/Olivia/Al в ~1 мин.
4. Ответить как клиент → Zap B должен сработать.
5. GHL: contact/opportunity (если `collect_phone` или funnel).

**Успех LIVE:** новый Yelp лид получает AI ответ без ручного действия.

---

## Шаг 7 — Ответ Alex

```
✅ Yelp Lead Responder LIVE
Smoke: PASS
Zap A (New Lead): ON
Zap B (Consumer Message): ON
E2E: [lead_id / скрин]
GHL env: set
```

---

## Ссылки

- [Yelp Zapier integration (official)](https://docs.developer.yelp.com/docs/leads-api-zapier-integration)
- `backend/README.md` — API и env
- `docs/ai-responder/BUILD_DONE.md` — deploy summary
- `backend/scripts/smoke_test_yelp_webhook.sh` — автопроверка
