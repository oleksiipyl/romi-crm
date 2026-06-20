from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Protocol

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.ai_responder import AIConversation, AIMessage
from app.services.ingest import record_outbound_message, record_tool_messages
from app.services.kb import KnowledgeBase, get_knowledge_base
from app.services.personas import AGENT_PERSONAS, get_agent_name
from app.services.state_machine import (
    apply_client_signal,
    detect_client_signal,
    has_project_description,
    next_state_after_tools,
    should_skip_ai_reply,
    state_guidance,
)
from app.services.tools import (
    TOOL_DEFINITIONS,
    execute_tool,
    get_price,
    message_contains_phone,
)

logger = logging.getLogger(__name__)

FAST_GLASS_SERVICES_BLURB = (
    "window glass, storefronts, shower doors, mirrors, and emergency board-ups"
)
BASE_PRICE_BLURB = (
    "single-pane from $349+, double-pane from $625+, storefront from $895+"
)

MSG1_LABEL = "MSG1:"
MSG2_LABEL = "MSG2:"


def parse_two_message_reply(content: str) -> tuple[str, str] | None:
    """Split AI output labeled MSG1 / MSG2 into two reply texts."""
    text = content.strip()
    if not text:
        return None
    match1 = re.search(
        r"MSG1:\s*(.+?)(?=MSG2:|$)",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    match2 = re.search(r"MSG2:\s*(.+?)$", text, flags=re.DOTALL | re.IGNORECASE)
    if not match1 or not match2:
        return None
    msg1 = match1.group(1).strip()
    msg2 = match2.group(1).strip()
    if not msg1 or not msg2:
        return None
    return msg1, msg2


def has_raq_project_description(conversation: AIConversation) -> bool:
    return has_project_description(conversation.metadata_)


def is_first_ai_turn(db: Session, conversation: AIConversation) -> bool:
    return (
        db.query(AIMessage.id)
        .filter(
            AIMessage.conversation_id == conversation.id,
            AIMessage.sender_type == "ai",
            AIMessage.content_type == "text",
        )
        .first()
        is None
    )

SYSTEM_PROMPT_TEMPLATE = """You are {agent_name}, a real team member at Fast Glass & Windows in Los Angeles. You text leads like a friendly local glass pro — warm, casual, confident. You're not a call center script. You sound like you're texting from your phone between jobs.

Your #1 job on every conversation: get their phone number. Only call collect_phone after the customer types their phone number in a message — never on your first reply and never using phone numbers from lead metadata.

How you talk: Keep it to 1-3 short sentences. Use contractions (I'll, we've, it's, don't). Light personality is good — "Totally get it!", "No worries!", "Happy to help!" Never sound corporate. Never say AI, bot, assistant, or automated. Never say "Certainly!", "Of course!", or "Please provide".

Opening vibe (vary it, don't copy word-for-word): "Hey [name]! This is {agent_name} from Fast Glass 👋 Happy to help with your window. What's the best number to reach you? I can call you right back with an exact price!"

If they ask price first: give a quick ballpark, then pivot to phone — "Prices depend on size and glass type — usually $400-800 for a standard window. Let me get you an exact number though. What's your phone? I'll call you in 2 min!"

If they resist calls ("just give me a price, no calls"): "Totally get it! For a standard double-pane it's usually $625-900. What size is the window roughly? I can text you a more exact number."

If they're impatient: "On it! Send me your number and I'll get you sorted fast — we do same-day for most jobs."

If they ask if you're a bot: "Haha nope, real person here 😄 Just move fast. So — best number to reach you?" Never confirm being AI.

After phone collected: "Perfect! Calling you shortly. We'll get this fixed today 💪"

If no phone after 2 messages, ask again differently. Don't book appointments yourself — specialist handles that. If manager joins, stop (human_takeover). After 3 unanswered follow-ups, stop responding.

CLIENT EXIT RULES (apply immediately when detected — do not pitch or ask for phone):
- STOP (stop / don't message / not interested / leave me alone): brief acknowledgment only, then end. No follow-ups.
- ALREADY BOOKED (already ordered / found someone / hired someone): friendly farewell, wish them well, state=complete.
- AGGRESSIVE (angry, rude, insults, harassment): de-escalate, apologize briefly, share business phone {company_phone}, step back, state=abandoned.

FIRST REPLY FORMAT (new Yelp leads only): Output exactly two labeled messages and nothing else:
MSG1: Exactly 2 short sentences — introduce yourself by name from Fast Glass and ask for their phone number for a callback quote.
MSG2: Service details for their described issue (or general Fast Glass services: window glass, storefront, shower doors, mirrors, emergency board-up) plus ballpark pricing. Use get_price when you can identify the service.

About Fast Glass & Windows: Local LA glass repair at 1730 Westwood Blvd. Family business, not corporate — licensed, insured, 1-year warranty, free estimates, 4.5 stars on Yelp. Same-day service, emergency 24/7. Greater LA, 100-mile radius.

Services: window glass replacement (single/double pane, IGU, tempered), storefront glass, shower doors, mirrors, emergency board-up, screen repair.

Ballpark prices (always say exact depends on size/type): single pane $349-749, double pane/IGU $625-1195, tempered $695-1225, storefront $895-2295, emergency board-up $299-649, shower door from $800. Use get_price tool when you can; these ranges are your backup.

Company phone: 213-566-8886

KNOWLEDGE BASE (service catalog excerpt):
{services_summary}

CURRENT CONVERSATION STATE:
{state_guidance}

LEAD CONTEXT:
{lead_context}
"""


class ChatClient(Protocol):
    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]: ...


class OpenAIChatClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key or "not-set")

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=400,
        )
        choice = response.choices[0]
        usage = response.usage
        return {
            "message": choice.message,
            "tokens_input": usage.prompt_tokens if usage else None,
            "tokens_output": usage.completion_tokens if usage else None,
        }


class AIBrain:
    def __init__(
        self,
        kb: KnowledgeBase | None = None,
        settings: Settings | None = None,
        client: ChatClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.kb = kb or get_knowledge_base()
        self._client = client

    @property
    def client(self) -> ChatClient:
        if self._client is None:
            self._client = OpenAIChatClient(self.settings)
        return self._client

    def _ensure_agent_name(self, conversation: AIConversation) -> str:
        meta = dict(conversation.metadata_ or {})
        if meta.get("agent_name") not in AGENT_PERSONAS:
            meta["agent_name"] = get_agent_name(meta)
            conversation.metadata_ = meta
        return str(meta["agent_name"])

    def _build_lead_context(self, conversation: AIConversation) -> str:
        meta = conversation.metadata_ or {}
        agent_name = meta.get("agent_name", AGENT_PERSONAS[0])
        lines = [
            f"Agent name: {agent_name}",
            f"Name: {meta.get('lead_name', 'Unknown')}",
            f"Channel: {conversation.channel}",
            f"ZIP: {conversation.zip_code or meta.get('zip_code', 'unknown')}",
            f"Phone: {meta.get('customer_phone') or meta.get('phone', 'not provided')}",
            f"Phone collected: {meta.get('phone_collected', False)}",
            f"Project: {meta.get('project_description') or meta.get('service_type', 'not specified')}",
            f"Current state: {conversation.state}",
        ]
        if conversation.price_quoted_min:
            lines.append(
                f"Quoted range: ${conversation.price_quoted_min}-${conversation.price_quoted_max}"
            )
        return "\n".join(lines)

    def _conversation_history(
        self, db: Session, conversation: AIConversation
    ) -> list[dict[str, Any]]:
        """Load text messages from DB so multi-turn context survives across requests."""
        rows = (
            db.query(AIMessage)
            .filter(
                AIMessage.conversation_id == conversation.id,
                AIMessage.content_type == "text",
                AIMessage.body.isnot(None),
            )
            .order_by(AIMessage.created_at)
            .all()
        )
        messages: list[dict[str, Any]] = []
        for msg in rows:
            if msg.sender_type == "ai":
                role = "assistant"
            elif msg.sender_type == "system":
                role = "system"
            else:
                role = "user"
            messages.append({"role": role, "content": msg.body or ""})
        return messages

    def _has_prior_ai_turn(self, db: Session, conversation: AIConversation) -> bool:
        return (
            db.query(AIMessage.id)
            .filter(
                AIMessage.conversation_id == conversation.id,
                AIMessage.sender_type == "ai",
                AIMessage.content_type == "text",
            )
            .first()
            is not None
        )

    def _build_system_prompt(self, conversation: AIConversation) -> str:
        agent_name = self._ensure_agent_name(conversation)
        company_phone = self.kb.company_phone() or "213-772-6882"
        return SYSTEM_PROMPT_TEMPLATE.format(
            agent_name=agent_name,
            company_phone=company_phone,
            services_summary=self.kb.services_summary(),
            state_guidance=state_guidance(conversation.state),
            lead_context=self._build_lead_context(conversation),
        )

    def _phone_ask_count(self, conversation: AIConversation) -> int:
        meta = conversation.metadata_ or {}
        return int(meta.get("phone_ask_count", 0))

    def _bump_phone_ask_count(self, db: Session, conversation: AIConversation) -> None:
        meta = dict(conversation.metadata_ or {})
        meta["phone_ask_count"] = self._phone_ask_count(conversation) + 1
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()

    def _phone_fallback_cta(self) -> str:
        phone = self.kb.company_phone() or "213-772-6882"
        return f"No worries! Call us at {phone} or drop your number here."

    def _finalize_outbound_reply(
        self,
        db: Session,
        conversation: AIConversation,
        reply_text: str,
        *,
        inbound_message: str | None,
        first_new_lead: bool,
    ) -> str:
        if inbound_message and not message_contains_phone(inbound_message):
            if self._phone_ask_count(conversation) >= 2:
                return self._phone_fallback_cta()
        if first_new_lead or self._reply_asks_for_phone(reply_text):
            self._bump_phone_ask_count(db, conversation)
        return reply_text

    @staticmethod
    def _reply_asks_for_phone(reply_text: str) -> bool:
        lowered = reply_text.lower()
        return any(
            phrase in lowered
            for phrase in (
                "what's your phone",
                "what's the best number",
                "best number to reach",
                "reach you",
                "call you back",
                "call right back",
                "send me your number",
            )
        )

    def _fallback_two_message_reply(
        self,
        conversation: AIConversation,
        *,
        has_description: bool,
    ) -> tuple[str, str]:
        meta = conversation.metadata_ or {}
        agent_name = self._ensure_agent_name(conversation)
        name = meta.get("lead_name", "there")
        project = (
            meta.get("project_description")
            or meta.get("service_type")
            or "your glass project"
        )

        msg1 = (
            f"Hey {name}! This is {agent_name} from Fast Glass. "
            f"What's the best number to reach you? I'll call right back with an exact quote!"
        )

        if has_description:
            service = self.kb.find_service_by_keywords(project)
            if service and conversation.zip_code:
                price = get_price(
                    self.kb,
                    service_id=service["service_id"],
                    zip_code=conversation.zip_code,
                )
                if "price_min" in price:
                    msg2 = (
                        f"We do {service['name'].lower()} and similar glass work all over LA. "
                        f"For your project, typical range is "
                        f"${price['price_min']:.0f}-${price['price_max']:.0f}."
                    )
                    return msg1, msg2
            msg2 = f"Happy to help with {project} — we handle all types of glass repair across LA."
            return msg1, msg2

        msg2 = (
            f"We handle {FAST_GLASS_SERVICES_BLURB} across LA. "
            f"Ballpark starting points: {BASE_PRICE_BLURB}."
        )
        return msg1, msg2

    def _record_ai_replies(
        self,
        db: Session,
        conversation: AIConversation,
        reply_text: str,
        *,
        reply_text_2: str = "",
        model: str,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        record_outbound_message(
            db,
            conversation,
            reply_text,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            channel=conversation.channel,
        )
        if reply_text_2:
            record_outbound_message(
                db,
                conversation,
                reply_text_2,
                model=model,
                channel=conversation.channel,
            )

    def _resolve_two_message_reply(
        self,
        conversation: AIConversation,
        content: str,
        *,
        has_description: bool,
    ) -> tuple[str, str]:
        parsed = parse_two_message_reply(content)
        if parsed:
            return parsed
        return self._fallback_two_message_reply(
            conversation,
            has_description=has_description,
        )

    def _fallback_reply(
        self,
        conversation: AIConversation,
        *,
        is_new_lead: bool,
        inbound_message: str | None,
        has_prior_turn: bool,
    ) -> str:
        meta = conversation.metadata_ or {}
        agent_name = self._ensure_agent_name(conversation)
        name = meta.get("lead_name", "there")
        project = meta.get("project_description") or meta.get("service_type") or "your window"

        if inbound_message:
            lowered = inbound_message.lower()
            if self._phone_ask_count(conversation) >= 2 and not message_contains_phone(
                inbound_message
            ):
                return self._phone_fallback_cta()

            if any(
                phrase in lowered
                for phrase in (
                    "are you a bot",
                    "are you ai",
                    "is this a bot",
                    "automated",
                    "real person",
                    "talk to a human",
                )
            ):
                return (
                    f"Haha nope, real person here 😄 Just move fast. "
                    f"So — best number to reach you, {name}?"
                )

            digits = [c for c in inbound_message if c.isdigit()]
            if len(digits) >= 7:
                return (
                    f"Perfect {name}! Calling you shortly — we'll get this fixed today 💪"
                )

            if any(w in lowered for w in ("no call", "no calls", "don't call", "just text", "just give me")):
                return (
                    f"Totally get it! For a standard double-pane it's usually $625-900. "
                    f"What size is the window roughly, {name}? I can text you a more exact number."
                )

            if any(w in lowered for w in ("hurry", "asap", "urgent", "today", "fast")):
                return (
                    f"On it! Send me your number and I'll get you sorted fast — "
                    f"we do same-day for most jobs."
                )

            service = self.kb.find_service_by_keywords(inbound_message)
            if service and conversation.zip_code:
                price = get_price(
                    self.kb,
                    service_id=service["service_id"],
                    zip_code=conversation.zip_code,
                )
                if "price_min" in price:
                    return (
                        f"Hey {name}! Prices depend on size and glass type — for {service['name']} "
                        f"we're usually ${price['price_min']:.0f}-${price['price_max']:.0f}. "
                        f"What's your phone? I'll call you in 2 min with an exact number!"
                    )

            if any(w in lowered for w in ("price", "cost", "how much", "quote", "$")):
                return (
                    f"Hey! Prices depend on size and glass type — usually $400-800 for a standard "
                    f"window. Let me get you an exact number though. What's your phone, {name}? "
                    f"I'll call you in 2 min!"
                )

            if has_prior_turn:
                return (
                    f"Still here, {name}! What's the best number to reach you? "
                    f"I'll call right back with an exact quote."
                )

        if has_prior_turn:
            return (
                f"Hey {name}, {agent_name} again from Fast Glass — still happy to help. "
                f"What's the best number to reach you?"
            )

        return (
            f"Hey {name}! This is {agent_name} from Fast Glass. "
            f"What's the best number to reach you?"
        )

    def generate_reply(
        self,
        db: Session,
        conversation: AIConversation,
        *,
        is_new_lead: bool = False,
        inbound_message: str | None = None,
    ) -> dict[str, Any]:
        if should_skip_ai_reply(conversation):
            return {
                "reply_text": "",
                "reply_text_2": "",
                "state": conversation.state,
                "fallback": True,
                "skipped": True,
            }

        if not conversation.ai_enabled:
            return {
                "reply_text": "A team member will respond shortly.",
                "reply_text_2": "",
                "state": conversation.state,
                "fallback": True,
            }

        if inbound_message:
            signal = detect_client_signal(inbound_message)
            if signal:
                reply = apply_client_signal(
                    db,
                    conversation,
                    signal,
                    company_phone=self.kb.company_phone() or "213-772-6882",
                )
                record_outbound_message(
                    db,
                    conversation,
                    reply,
                    model="client-signal",
                    channel=conversation.channel,
                )
                db.commit()
                return {
                    "reply_text": reply,
                    "reply_text_2": "",
                    "state": conversation.state,
                    "fallback": True,
                    "client_signal": signal,
                }

        has_prior_turn = self._has_prior_ai_turn(db, conversation)
        first_new_lead = (
            is_new_lead
            and not inbound_message
            and not has_prior_turn
        )
        has_description = has_raq_project_description(conversation)

        if first_new_lead and has_description and conversation.state == "greet":
            conversation.state = "qualify"
            db.add(conversation)
            db.flush()

        if not self.settings.openai_api_key:
            if first_new_lead:
                reply_text, reply_text_2 = self._fallback_two_message_reply(
                    conversation,
                    has_description=has_description,
                )
                self._bump_phone_ask_count(db, conversation)
                self._record_ai_replies(
                    db,
                    conversation,
                    reply_text,
                    reply_text_2=reply_text_2,
                    model="fallback",
                )
                db.commit()
                return {
                    "reply_text": reply_text,
                    "reply_text_2": reply_text_2,
                    "state": conversation.state,
                    "fallback": True,
                }

            reply = self._fallback_reply(
                conversation,
                is_new_lead=is_new_lead,
                inbound_message=inbound_message,
                has_prior_turn=has_prior_turn,
            )
            reply = self._finalize_outbound_reply(
                db,
                conversation,
                reply,
                inbound_message=inbound_message,
                first_new_lead=False,
            )
            record_outbound_message(
                db,
                conversation,
                reply,
                model="fallback",
                channel=conversation.channel,
            )
            db.commit()
            return {
                "reply_text": reply,
                "reply_text_2": "",
                "state": conversation.state,
                "fallback": True,
            }

        system_prompt = self._build_system_prompt(conversation)
        history = self._conversation_history(db, conversation)

        if first_new_lead:
            agent_name = self._ensure_agent_name(conversation)
            meta = conversation.metadata_ or {}
            project = meta.get("project_description") or meta.get("service_type") or "their glass project"
            if has_description:
                user_content = (
                    f"New Yelp lead just arrived. You are {agent_name}. "
                    f"Their project description: {project}. "
                    "Send the first reply using the FIRST REPLY FORMAT with MSG1 and MSG2. "
                    "MSG1: 2 sentences — introduce yourself by name and ask for phone. "
                    "MSG2: acknowledge their glass issue, use get_price for a ballpark quote "
                    "when you can identify the service."
                )
            else:
                user_content = (
                    f"New Yelp lead just arrived. You are {agent_name}. "
                    "No project description was provided. Send the first reply using the "
                    "FIRST REPLY FORMAT with MSG1 and MSG2. "
                    "MSG1: 2 sentences — introduce yourself by name and ask for phone. "
                    "MSG2: describe Fast Glass services (window glass, storefront, shower "
                    "doors, mirrors, emergency board-up) and starting ballpark prices "
                    "(single pane $349+, double pane $625+, storefront $895+)."
                )
        elif inbound_message:
            user_content = inbound_message
        else:
            user_content = "Continue the conversation based on current state."

        api_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_content},
        ]

        tools_called: list[str] = []
        total_tokens_in = 0
        total_tokens_out = 0
        start = time.monotonic()

        try:
            for _ in range(5):
                result = self.client.generate(api_messages, TOOL_DEFINITIONS)
                message = result["message"]
                total_tokens_in += result.get("tokens_input") or 0
                total_tokens_out += result.get("tokens_output") or 0

                if message.tool_calls:
                    api_messages.append(
                        {
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                }
                                for tc in message.tool_calls
                            ],
                        }
                    )
                    for tc in message.tool_calls:
                        fn_name = tc.function.name
                        fn_args = json.loads(tc.function.arguments or "{}")
                        tool_result = execute_tool(
                            fn_name,
                            fn_args,
                            kb=self.kb,
                            db=db,
                            conversation=conversation,
                            inbound_message=inbound_message,
                            first_new_lead=first_new_lead,
                        )
                        if tool_result.get("status") != "rejected":
                            tools_called.append(fn_name)
                        record_tool_messages(
                            db,
                            conversation,
                            fn_name,
                            fn_args,
                            tool_result,
                            channel=conversation.channel,
                        )
                        api_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps(tool_result),
                            }
                        )
                    continue

                raw_content = (message.content or "").strip()
                if first_new_lead:
                    if raw_content:
                        reply_text, reply_text_2 = self._resolve_two_message_reply(
                            conversation,
                            raw_content,
                            has_description=has_description,
                        )
                    else:
                        reply_text, reply_text_2 = self._fallback_two_message_reply(
                            conversation,
                            has_description=has_description,
                        )
                    self._bump_phone_ask_count(db, conversation)
                else:
                    reply_text = raw_content
                    reply_text_2 = ""
                    if not reply_text:
                        reply_text = self._fallback_reply(
                            conversation,
                            is_new_lead=is_new_lead,
                            inbound_message=inbound_message,
                            has_prior_turn=has_prior_turn,
                        )
                    reply_text = self._finalize_outbound_reply(
                        db,
                        conversation,
                        reply_text,
                        inbound_message=inbound_message,
                        first_new_lead=False,
                    )

                conversation.state = next_state_after_tools(
                    conversation.state,
                    tools_called,
                    is_new_lead=is_new_lead,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                self._record_ai_replies(
                    db,
                    conversation,
                    reply_text,
                    reply_text_2=reply_text_2,
                    model=self.settings.openai_model,
                    tokens_input=total_tokens_in,
                    tokens_output=total_tokens_out,
                    latency_ms=latency_ms,
                )
                db.commit()

                return {
                    "reply_text": reply_text,
                    "reply_text_2": reply_text_2,
                    "state": conversation.state,
                    "tools_called": tools_called,
                    "latency_ms": latency_ms,
                    "fallback": False,
                }

            if first_new_lead:
                reply_text, reply_text_2 = self._fallback_two_message_reply(
                    conversation,
                    has_description=has_description,
                )
                self._record_ai_replies(
                    db,
                    conversation,
                    reply_text,
                    reply_text_2=reply_text_2,
                    model="fallback",
                )
            else:
                reply_text = self._fallback_reply(
                    conversation,
                    is_new_lead=is_new_lead,
                    inbound_message=inbound_message,
                    has_prior_turn=has_prior_turn,
                )
                reply_text_2 = ""
                record_outbound_message(db, conversation, reply_text, model="fallback")
            db.commit()
            return {
                "reply_text": reply_text,
                "reply_text_2": reply_text_2,
                "state": conversation.state,
                "tools_called": tools_called,
                "fallback": True,
            }

        except Exception:
            logger.exception("AI brain error for conversation %s", conversation.id)
            if first_new_lead:
                reply_text, reply_text_2 = self._fallback_two_message_reply(
                    conversation,
                    has_description=has_description,
                )
                self._record_ai_replies(
                    db,
                    conversation,
                    reply_text,
                    reply_text_2=reply_text_2,
                    model="fallback-error",
                )
            else:
                reply_text = self._fallback_reply(
                    conversation,
                    is_new_lead=is_new_lead,
                    inbound_message=inbound_message,
                    has_prior_turn=has_prior_turn,
                )
                reply_text_2 = ""
                record_outbound_message(
                    db, conversation, reply_text, model="fallback-error"
                )
            db.commit()
            return {
                "reply_text": reply_text,
                "reply_text_2": reply_text_2,
                "state": conversation.state,
                "fallback": True,
                "error": True,
            }


def get_ai_brain() -> AIBrain:
    return AIBrain()
