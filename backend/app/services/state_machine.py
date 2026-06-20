from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.ai_responder import AIConversation
from app.services.kb import get_knowledge_base
from app.services.personas import AGENT_PERSONAS

VALID_STATES = {
    "idle",
    "greet",
    "qualify",
    "offer",
    "close",
    "callback",
    "voice_active",
    "human_active",
    "complete",
    "retry_sms",
    "follow_up_queued",
    "abandoned",
}

# Hours to wait after last outbound before each follow-up attempt.
FOLLOW_UP_INTERVALS_HOURS = [24, 48, 48]
MAX_FOLLOW_UP_ATTEMPTS = 3


def has_project_description(metadata: dict[str, Any] | None) -> bool:
    """True when RAQ payload included a meaningful project description."""
    if not metadata:
        return False
    for key in ("project_description", "service_type"):
        value = metadata.get(key)
        if not value:
            continue
        text = str(value).strip()
        if text and text.lower() not in {"not specified", "unknown", "n/a"}:
            return True
    return False


def initial_state_for_event(
    is_new_lead: bool,
    has_lead_reply: bool,
    *,
    has_project_description: bool = False,
) -> str:
    if is_new_lead and not has_lead_reply:
        if has_project_description:
            return "qualify"
        return "greet"
    if has_lead_reply:
        return "qualify"
    return "greet"


def next_state_after_tools(
    current_state: str,
    tools_called: list[str],
    *,
    is_new_lead: bool,
) -> str:
    if "human_takeover" in tools_called or "escalate_to_human" in tools_called:
        return "human_active"
    if "collect_phone" in tools_called:
        return "human_active"
    if "book_estimate" in tools_called:
        return "complete"
    if "trigger_callback" in tools_called:
        return "callback"
    if "get_price" in tools_called:
        return "offer"
    if is_new_lead and current_state == "idle":
        return "greet"
    if current_state == "greet":
        return "qualify"
    return current_state


def state_guidance(state: str) -> str:
    guidance = {
        "greet": (
            "Just got this lead. Introduce yourself by first name (Robert, Olivia, or Al). "
            "Acknowledge their glass issue in one line. Ask for their phone number naturally — "
            "you'll call them right back with an exact quote."
        ),
        "qualify": (
            "Keep it casual. You can drop a ballpark price if they asked, but always steer back "
            "to getting their phone number for an exact quote on a quick call."
        ),
        "offer": (
            "You shared a ballpark — now pivot: 'Let me get you an exact number. What's your phone? "
            "I'll call you in 2 min!' Don't let the convo end without their number."
        ),
        "callback": (
            "Phone's in — confirm you're calling them shortly. Keep it short and upbeat."
        ),
        "close": (
            "Phone collected. Confirm callback shortly. Don't book appointments yourself."
        ),
        "human_active": (
            "Manager jumped in — stay quiet, don't respond."
        ),
        "abandoned": (
            "They ghosted after follow-ups — don't message."
        ),
    }
    return guidance.get(state, "Focus on getting their phone number.")


def _follow_up_count(conversation: AIConversation) -> int:
    meta = conversation.metadata_ or {}
    return int(meta.get("follow_up_count", 0))


def _last_follow_up_at(conversation: AIConversation) -> datetime | None:
    meta = conversation.metadata_ or {}
    raw = meta.get("last_follow_up_at")
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def is_abandoned(conversation: AIConversation) -> bool:
    return conversation.state == "abandoned" or not conversation.ai_enabled


def should_send_follow_up(
    conversation: AIConversation,
    now: datetime | None = None,
) -> bool:
    """True when a timed follow-up is due (no lead reply since last outbound)."""
    if now is None:
        now = datetime.now(timezone.utc)

    if conversation.state in {"complete", "human_active", "abandoned"}:
        return False
    if (conversation.metadata_ or {}).get("phone_collected"):
        return False
    if _follow_up_count(conversation) >= MAX_FOLLOW_UP_ATTEMPTS:
        return False

    anchor = conversation.last_ai_message_at or conversation.first_response_at
    if anchor is None:
        return False

    if conversation.last_message_at and conversation.last_ai_message_at:
        if conversation.last_message_at > conversation.last_ai_message_at:
            return False

    count = _follow_up_count(conversation)
    last_fu = _last_follow_up_at(conversation)
    if last_fu is not None:
        anchor = last_fu

    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)

    interval = FOLLOW_UP_INTERVALS_HOURS[min(count, len(FOLLOW_UP_INTERVALS_HOURS) - 1)]
    return now >= anchor + timedelta(hours=interval)


def build_follow_up_message(conversation: AIConversation) -> str:
    meta = conversation.metadata_ or {}
    name = meta.get("lead_name", "there")
    agent = meta.get("agent_name", AGENT_PERSONAS[0])
    project = meta.get("project_description") or meta.get("service_type") or "your glass project"
    count = _follow_up_count(conversation) + 1

    if count >= MAX_FOLLOW_UP_ATTEMPTS:
        kb = get_knowledge_base()
        presentation = kb.abandon_presentation(name)
        if presentation:
            return presentation

    if count == 1:
        return (
            f"Hey {name}, it's {agent} from Fast Glass — just checking in on "
            f"{project}. What's the best number to reach you? I'll call right back!"
        )
    if count == 2:
        return (
            f"Hey {name}, {agent} again from Fast Glass. Still happy to help with "
            f"{project}. Can I get a good callback number?"
        )
    return (
        f"Last check-in, {name} — {agent} at Fast Glass. Shoot me your number "
        f"and I'll call you right back."
    )


def apply_follow_up(
    conversation: AIConversation,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """
    If follow-up is due, update metadata/state and return message payload.
    After MAX_FOLLOW_UP_ATTEMPTS, mark conversation abandoned.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if not should_send_follow_up(conversation, now):
        if _follow_up_count(conversation) >= MAX_FOLLOW_UP_ATTEMPTS:
            conversation.state = "abandoned"
            conversation.ai_enabled = False
        return None

    meta = dict(conversation.metadata_ or {})
    count = int(meta.get("follow_up_count", 0)) + 1
    meta["follow_up_count"] = count
    meta["last_follow_up_at"] = now.isoformat()
    conversation.metadata_ = meta
    conversation.state = "follow_up_queued"

    if count >= MAX_FOLLOW_UP_ATTEMPTS:
        message = build_follow_up_message(conversation)
        conversation.state = "abandoned"
        conversation.ai_enabled = False
        conversation.outcome = "abandoned"
        return {
            "message": message,
            "follow_up_number": count,
            "final": True,
            "presentation": True,
        }

    return {"message": build_follow_up_message(conversation), "follow_up_number": count, "final": False}
