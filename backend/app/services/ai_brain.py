from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.ai_responder import AIConversation, AIMessage
from app.services.ingest import record_outbound_message, record_tool_messages
from app.services.kb import KnowledgeBase, get_knowledge_base
from app.services.state_machine import next_state_after_tools, state_guidance
from app.services.tools import TOOL_DEFINITIONS, execute_tool, get_price

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are the AI assistant for Fast Glass & Windows, Los Angeles's trusted glass repair company.

{company_context}

KNOWLEDGE BASE (service catalog excerpt):
{services_summary}

RULES:
1. Be warm, professional, concise. Use the lead's first name when known.
2. NEVER quote exact prices without calling get_price first.
3. Always offer a callback in ~30 seconds for complex jobs (use trigger_callback only after explicit consent).
4. Keep Yelp chat replies SHORT — 1-3 sentences max.
5. Goal: respond fast, qualify the lead, close to estimate booking or callback.
6. For emergencies (broken glass, injury), call escalate_to_human immediately.
7. Service area: greater LA within 100 miles of Westwood. Use ZIP to verify.

STATE MACHINE GUIDANCE:
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
            max_tokens=300,
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

    def _build_lead_context(self, conversation: AIConversation) -> str:
        meta = conversation.metadata_ or {}
        lines = [
            f"Name: {meta.get('lead_name', 'Unknown')}",
            f"Channel: {conversation.channel}",
            f"ZIP: {conversation.zip_code or meta.get('zip_code', 'unknown')}",
            f"Phone: {meta.get('phone', 'not provided')}",
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
        return SYSTEM_PROMPT_TEMPLATE.format(
            company_context=self.kb.build_context_block(),
            services_summary=self.kb.services_summary(),
            state_guidance=state_guidance(conversation.state),
            lead_context=self._build_lead_context(conversation),
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
        name = meta.get("lead_name", "there")
        project = meta.get("project_description") or meta.get("service_type") or "your glass project"

        if is_new_lead and not inbound_message and not has_prior_turn:
            return (
                f"Hi {name}! Thanks for reaching out to Fast Glass & Windows about {project}. "
                f"I'm Alex's assistant — I can get you a ballpark price or call you back in 30 seconds. "
                f"What works better?"
            )

        if inbound_message:
            lowered = inbound_message.lower()
            if any(ch.isdigit() for ch in inbound_message) and (
                "phone" in lowered or "call" in lowered or "number" in lowered or "+" in inbound_message
            ):
                return (
                    f"Thanks {name}! Got your number — we'll call you back shortly to discuss {project}."
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
                        f"For {service['name']}, typical range is "
                        f"${price['price_min']:.0f}-${price['price_max']:.0f}. "
                        f"Want to book a free estimate or get a quick callback?"
                    )
            if has_prior_turn:
                return (
                    f"Thanks {name}! I have your message — moving your request forward now. "
                    f"A team member can call you shortly if you'd like."
                )
            return (
                f"Thanks {name}! Can you share the glass size and your ZIP code "
                f"so I can get you an accurate ballpark?"
            )

        if has_prior_turn:
            return (
                f"Thanks {name}! We're still on your {project} request — "
                f"reply with any details and we'll take it from here."
            )

        return (
            f"Hi {name}! Fast Glass & Windows here — how can we help with your glass needs today?"
        )

    def generate_reply(
        self,
        db: Session,
        conversation: AIConversation,
        *,
        is_new_lead: bool = False,
        inbound_message: str | None = None,
    ) -> dict[str, Any]:
        if not conversation.ai_enabled:
            return {
                "reply_text": "A team member will respond shortly.",
                "state": conversation.state,
                "fallback": True,
            }

        has_prior_turn = self._has_prior_ai_turn(db, conversation)

        if not self.settings.openai_api_key:
            reply = self._fallback_reply(
                conversation,
                is_new_lead=is_new_lead,
                inbound_message=inbound_message,
                has_prior_turn=has_prior_turn,
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
                "state": conversation.state,
                "fallback": True,
            }

        system_prompt = self._build_system_prompt(conversation)
        history = self._conversation_history(db, conversation)

        if is_new_lead and not inbound_message and not has_prior_turn:
            user_content = (
                "New Yelp lead just arrived. Send the first greeting message. "
                "Do not wait for the customer to message first."
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
                        )
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

                reply_text = (message.content or "").strip()
                if not reply_text:
                    reply_text = self._fallback_reply(
                        conversation,
                        is_new_lead=is_new_lead,
                        inbound_message=inbound_message,
                        has_prior_turn=has_prior_turn,
                    )

                conversation.state = next_state_after_tools(
                    conversation.state,
                    tools_called,
                    is_new_lead=is_new_lead,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                record_outbound_message(
                    db,
                    conversation,
                    reply_text,
                    model=self.settings.openai_model,
                    tokens_input=total_tokens_in,
                    tokens_output=total_tokens_out,
                    latency_ms=latency_ms,
                    channel=conversation.channel,
                )
                db.commit()

                return {
                    "reply_text": reply_text,
                    "state": conversation.state,
                    "tools_called": tools_called,
                    "latency_ms": latency_ms,
                    "fallback": False,
                }

            reply_text = self._fallback_reply(
                conversation,
                is_new_lead=is_new_lead,
                inbound_message=inbound_message,
                has_prior_turn=has_prior_turn,
            )
            record_outbound_message(db, conversation, reply_text, model="fallback")
            db.commit()
            return {
                "reply_text": reply_text,
                "state": conversation.state,
                "tools_called": tools_called,
                "fallback": True,
            }

        except Exception:
            logger.exception("AI brain error for conversation %s", conversation.id)
            reply_text = self._fallback_reply(
                conversation,
                is_new_lead=is_new_lead,
                inbound_message=inbound_message,
                has_prior_turn=has_prior_turn,
            )
            record_outbound_message(db, conversation, reply_text, model="fallback-error")
            db.commit()
            return {
                "reply_text": reply_text,
                "state": conversation.state,
                "fallback": True,
                "error": True,
            }


def get_ai_brain() -> AIBrain:
    return AIBrain()
