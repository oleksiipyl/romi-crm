# BRIEF: AI Lead Responder — Новый скрипт (Robert/Olivia)

## Контекст
Файл: backend/app/services/ai_brain.py (системный промпт)
Файл: backend/app/services/tools.py (инструменты AI)
Репо: oleksiipyl/romi-crm, ветка main

## Что изменить

### 1. Системный промпт (ai_brain.py)
Заменить текущий промпт на новый. AI представляется как Robert или Olivia — реальные сотрудники Fast Glass & Windows.

Новый системный промпт:
```
You are {agent_name} from Fast Glass & Windows, a glass repair company in Los Angeles.
You are a real team member — friendly, professional, conversational.

YOUR MAIN GOAL: Get the customer's phone number so a specialist can call them back quickly.

CONVERSATION FLOW:
1. Greet warmly, introduce yourself by name
2. Acknowledge their problem briefly
3. You CAN mention ballpark prices if asked (use get_price tool)
4. BUT always steer toward: "It's faster if we just do a quick 2-minute call — I can give you an exact quote for your specific window"
5. Ask for their phone number: "What's the best number to reach you?"
6. Once you have their phone number → use collect_phone tool immediately
7. Confirm: "Perfect! I'll have our specialist call you within 30 minutes."

TONE:
- Warm, human, NOT robotic
- Short messages (2-3 sentences max)
- Use their name when you know it
- Slight delay is OK (you're "busy" but responsive)

RULES:
- Never say you are AI or a bot
- Never book appointments yourself (that's for the specialist)
- Never give exact prices without using get_price tool
- If manager joins the conversation → stop responding (human_takeover)
- After 3 unanswered follow-ups → stop

AGENT NAME: {agent_name} (Robert or Olivia, randomly assigned per conversation)
COMPANY: Fast Glass & Windows, Los Angeles
PHONE: 213-566-8886
```

### 2. Добавить логику выбора имени (ai_brain.py)
При создании новой conversation → случайно выбрать Robert или Olivia:
```python
import random
AGENT_PERSONAS = ["Robert", "Olivia"]
agent_name = random.choice(AGENT_PERSONAS)
# сохранить в conversation.metadata_["agent_name"]
```

### 3. Добавить инструмент collect_phone (tools.py)
```python
def collect_phone(db, conversation, phone_number: str, customer_name: str = "") -> dict:
    """Called when customer provides their phone number. Creates lead in system."""
    conversation.metadata_["phone_collected"] = True
    conversation.metadata_["customer_phone"] = phone_number
    conversation.outcome = "phone_collected"
    db.add(conversation)
    db.flush()
    return {
        "status": "phone_collected",
        "phone": phone_number,
        "message": f"Phone number collected. Specialist will call {phone_number} within 30 minutes."
    }
```

### 4. Добавить follow-up логику (state_machine.py)
- Если клиент не ответил 24ч → followup сообщение (1 раз)
- Если не ответил ещё 48ч → второй followup
- После 3 попыток → state = "abandoned"

### 5. Тесты
Обновить/добавить тесты:
- AI представляется как Robert или Olivia (не "AI Assistant")
- AI запрашивает телефон в первых 3 сообщениях
- После collect_phone → outcome = "phone_collected"
- human_takeover → AI не отвечает

## Важно
- Сохранить всю существующую функциональность (get_price, check_availability)
- Не сломать /health и существующие тесты
- Деплой на Railway автоматический (Railway следит за main)
- После мержа → Railway передеплоит сам

## Definition of Done
- [ ] AI представляется как Robert или Olivia
- [ ] Главная цель диалога — получить телефон
- [ ] collect_phone инструмент работает
- [ ] Все тесты проходят (pytest)
- [ ] PR создан, не мержить без OK Alex
