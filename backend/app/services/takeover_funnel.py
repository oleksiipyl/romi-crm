from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from sqlalchemy.orm import Session

from app.models.ai_responder import AIConversation
from app.services.contact_check import check_existing_contact
from app.services.ghl import GHLClient, ensure_early_yelp_contact, get_ghl_client
from app.services.tools import human_takeover

logger = logging.getLogger(__name__)

FunnelAction = Literal["continue_ai", "takeover_after_first", "skip_ai"]


@dataclass
class FunnelDecision:
    action: FunnelAction
    contact_check: dict[str, Any]
    notify_message: str | None = None
    notify_title: str = "Yelp AI Responder"


def _build_notify_message(
    contact_check: dict[str, Any],
    lead_name: str,
) -> tuple[str | None, str]:
    confidence = contact_check.get("match_confidence", "none")
    in_progress = contact_check.get("in_progress", False)
    owner = contact_check.get("owner")

    if confidence == "strong" and in_progress:
        owner_part = f" (owner: {owner})" if owner else ""
        return (
            f"Yelp от существующего контакта{owner_part} — {lead_name} пишет снова. "
            f"Ответь сам.",
            "Yelp — existing in-progress contact",
        )

    if confidence == "strong" and contact_check.get("exists"):
        return (
            f"Известный контакт пишет в Yelp — {lead_name}. AI передал менеджеру после "
            f"нейтрального приветствия.",
            "Yelp — known contact",
        )

    if confidence == "weak":
        return (
            f"Возможно существующий контакт — {lead_name}. Проверь совпадение в CRM.",
            "Yelp — possible existing contact",
        )

    return None, "Yelp AI Responder"


def evaluate_post_first_reply(
    db: Session,
    conversation: AIConversation,
    normalized: dict[str, Any],
    *,
    ghl_client: GHLClient | None = None,
) -> FunnelDecision:
    """
    Run CRM lookup AFTER the first reply was sent.
    Existing contacts → human_takeover; new contacts → phone-first from message 2.
    """
    ensure_early_yelp_contact(db, conversation, ghl_client=ghl_client)

    meta = dict(conversation.metadata_ or {})
    phone = normalized.get("phone") or meta.get("phone") or meta.get("customer_phone")
    name = normalized.get("name") or meta.get("lead_name")

    try:
        contact_check = check_existing_contact(phone, name, ghl_client=ghl_client)
    except httpx.TimeoutException:
        logger.warning("GHL contact check timed out — deferring for conversation %s", conversation.id)
        contact_check = {
            "exists": False,
            "in_progress": False,
            "owner": None,
            "match_confidence": "none",
            "contact_id": None,
            "timed_out": True,
            "defer_check": True,
        }

    meta["contact_check"] = contact_check
    meta["contact_check_phase"] = "post_first_reply"
    conversation.metadata_ = meta
    db.add(conversation)
    db.flush()

    if contact_check.get("timed_out") or contact_check.get("defer_check"):
        meta["contact_check_pending"] = True
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()
        return FunnelDecision(action="continue_ai", contact_check=contact_check)

    notify_message, notify_title = _build_notify_message(
        contact_check,
        str(name or "lead"),
    )

    if contact_check.get("exists"):
        ghl = ghl_client or get_ghl_client()
        if notify_message:
            ghl.notify_manager(
                notify_message,
                contact_id=contact_check.get("contact_id"),
                title=notify_title,
            )
        human_takeover(
            db,
            conversation,
            reason="Existing contact identified after neutral first reply",
        )
        meta["takeover_reason"] = "existing_after_first_reply"
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()
        return FunnelDecision(
            action="takeover_after_first",
            contact_check=contact_check,
            notify_message=notify_message,
            notify_title=notify_title,
        )

    meta["phone_first_from_next"] = True
    conversation.metadata_ = meta
    db.add(conversation)
    db.flush()
    return FunnelDecision(action="continue_ai", contact_check=contact_check)


def evaluate_inbound_contact(
    db: Session,
    conversation: AIConversation,
    normalized: dict[str, Any],
    *,
    ghl_client: GHLClient | None = None,
) -> FunnelDecision:
    """Pre-reply check for follow-up messages (message 2+)."""
    meta = dict(conversation.metadata_ or {})
    if conversation.state == "human_active" or not conversation.ai_enabled:
        return FunnelDecision(
            action="skip_ai",
            contact_check=meta.get("contact_check", {}),
        )

    phone = normalized.get("phone") or meta.get("phone") or meta.get("customer_phone")
    name = normalized.get("name") or meta.get("lead_name")

    try:
        contact_check = check_existing_contact(phone, name, ghl_client=ghl_client)
    except httpx.TimeoutException:
        contact_check = {
            "exists": False,
            "match_confidence": "none",
            "timed_out": True,
            "defer_check": True,
        }

    meta["contact_check"] = contact_check
    conversation.metadata_ = meta
    db.add(conversation)
    db.flush()

    if contact_check.get("exists") and contact_check.get("in_progress"):
        notify_message, notify_title = _build_notify_message(contact_check, str(name or "lead"))
        ghl = ghl_client or get_ghl_client()
        if notify_message:
            ghl.notify_manager(
                notify_message,
                contact_id=contact_check.get("contact_id"),
                title=notify_title,
            )
        human_takeover(db, conversation, reason="Existing in-progress contact on follow-up")
        return FunnelDecision(action="skip_ai", contact_check=contact_check)

    return FunnelDecision(action="continue_ai", contact_check=contact_check)
