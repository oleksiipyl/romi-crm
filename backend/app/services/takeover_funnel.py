from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.ai_responder import AIConversation
from app.services.contact_check import check_existing_contact
from app.services.ghl import GHLClient, get_ghl_client
from app.services.tools import human_takeover

logger = logging.getLogger(__name__)

FunnelAction = Literal["skip_ai", "continue_ai"]


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
            f"Известный контакт пишет в Yelp — {lead_name}. AI отвечает, но проверь диалог.",
            "Yelp — known contact",
        )

    if confidence == "weak":
        return (
            f"Возможно существующий контакт — {lead_name}. Проверь совпадение в CRM.",
            "Yelp — possible existing contact",
        )

    return None, "Yelp AI Responder"


def evaluate_inbound_contact(
    db: Session,
    conversation: AIConversation,
    normalized: dict[str, Any],
    *,
    ghl_client: GHLClient | None = None,
) -> FunnelDecision:
    """Proactive CRM lookup before AI replies to a Yelp consumer message."""
    meta = dict(conversation.metadata_ or {})
    phone = normalized.get("phone") or meta.get("phone") or meta.get("customer_phone")
    name = normalized.get("name") or meta.get("lead_name")

    contact_check = check_existing_contact(phone, name, ghl_client=ghl_client)
    meta["contact_check"] = contact_check
    conversation.metadata_ = meta
    db.add(conversation)
    db.flush()

    notify_message, notify_title = _build_notify_message(
        contact_check,
        str(name or "lead"),
    )

    if (
        contact_check.get("match_confidence") == "strong"
        and contact_check.get("in_progress")
    ):
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
            reason="Existing in-progress contact messaged on Yelp",
        )
        meta["takeover_reason"] = "existing_in_progress"
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()
        return FunnelDecision(
            action="skip_ai",
            contact_check=contact_check,
            notify_message=notify_message,
            notify_title=notify_title,
        )

    if notify_message:
        ghl = ghl_client or get_ghl_client()
        ghl.notify_manager(
            notify_message,
            contact_id=contact_check.get("contact_id"),
            title=notify_title,
        )
        meta["manager_notified"] = True
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()

    return FunnelDecision(
        action="continue_ai",
        contact_check=contact_check,
        notify_message=notify_message,
        notify_title=notify_title,
    )
