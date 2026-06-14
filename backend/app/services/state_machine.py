from __future__ import annotations

from typing import Any


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
}


def initial_state_for_event(is_new_lead: bool, has_lead_reply: bool) -> str:
    if is_new_lead and not has_lead_reply:
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
    if "escalate_to_human" in tools_called:
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
            "GREET: Send a warm first reply. Reference their project. "
            "Offer a ballpark price OR a 30-second callback. Keep under 3 sentences."
        ),
        "qualify": (
            "QUALIFY: Ask service type, dimensions, ZIP if missing. "
            "Use get_price when you have enough info. Identify service_id from catalog."
        ),
        "offer": (
            "OFFER: Present price range from get_price. "
            "Ask if they want to book an estimate or get a callback in 30 seconds."
        ),
        "callback": (
            "CALLBACK: Confirm callback consent. Use trigger_callback with phone and context. "
            "Tell them we'll call in ~30 seconds."
        ),
        "close": (
            "CLOSE: Use book_estimate when they agree to schedule. Confirm details."
        ),
        "human_active": (
            "HANDOFF: Acknowledge escalation. A human will follow up shortly."
        ),
    }
    return guidance.get(state, f"Current state: {state}. Continue helping the lead.")
