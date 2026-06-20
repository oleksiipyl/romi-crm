from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_responder import AIConversation
from app.services.contact_check import check_existing_contact
from app.services.ghl import GHLClient, get_ghl_client
from app.services.kb import KnowledgeBase

logger = logging.getLogger(__name__)

MIN_PHONE_DIGITS = 7


def message_contains_phone(text: str | None) -> bool:
    """True when the customer's message includes enough digits to be a phone number."""
    if not text:
        return False
    digits = [c for c in text if c.isdigit()]
    return len(digits) >= MIN_PHONE_DIGITS


def may_invoke_collect_phone(
    *,
    inbound_message: str | None,
    first_new_lead: bool,
) -> bool:
    """collect_phone only after the customer shares a number in their own message."""
    if first_new_lead:
        return False
    return message_contains_phone(inbound_message)


def get_price(
    kb: KnowledgeBase,
    service_id: str,
    zip_code: str,
    width_inches: float | None = None,
    height_inches: float | None = None,
    glass_type: str = "unknown",
) -> dict[str, Any]:
    service = kb.get_service(service_id)
    if not service:
        return {"error": f"Unknown service_id: {service_id}"}

    price_min = float(service["base_price_min"])
    price_max = float(service["base_price_max"])

    if width_inches and height_inches:
        sqft = (width_inches * height_inches) / 144
        multiplier = max(1.0, sqft / 6)
        price_min = round(price_min * multiplier, 2)
        price_max = round(price_max * multiplier, 2)

    if glass_type == "tempered":
        price_min = round(price_min * 1.15, 2)
        price_max = round(price_max * 1.15, 2)
    elif glass_type == "laminated":
        price_min = round(price_min * 1.25, 2)
        price_max = round(price_max * 1.25, 2)
    elif glass_type == "low_e":
        price_min = round(price_min * 1.2, 2)
        price_max = round(price_max * 1.2, 2)

    in_zone = kb.is_in_service_zone(zip_code)
    return {
        "service_id": service_id,
        "service_name": service["name"],
        "price_min": price_min,
        "price_max": price_max,
        "currency": "USD",
        "in_service_zone": in_zone,
        "note": "Ballpark estimate — final price confirmed at in-home measure.",
        "requires_measure": service.get("requires_measure", True),
    }


def book_estimate(
    db: Session,
    conversation: AIConversation,
    contact_name: str,
    phone: str,
    zip_code: str,
    service_id: str,
    address: str | None = None,
    preferred_datetime: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    booking_id = str(uuid.uuid4())
    conversation.service_id = service_id
    conversation.zip_code = zip_code
    conversation.outcome = "booked"
    conversation.outcome_detail = {
        "booking_id": booking_id,
        "contact_name": contact_name,
        "phone": phone,
        "address": address,
        "preferred_datetime": preferred_datetime,
        "notes": notes,
        "booked_at": datetime.now(timezone.utc).isoformat(),
    }
    conversation.state = "complete"
    conversation.completed_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.flush()

    return {
        "booking_id": booking_id,
        "status": "scheduled",
        "message": (
            f"Estimate booked for {contact_name}. "
            f"We'll confirm your appointment shortly."
        ),
        "preferred_datetime": preferred_datetime,
        "service_id": service_id,
    }


def collect_phone(
    db: Session,
    conversation: AIConversation,
    phone_number: str,
    customer_name: str = "",
    *,
    ghl_client: GHLClient | None = None,
) -> dict[str, Any]:
    """Called when customer provides their phone number."""
    meta = dict(conversation.metadata_ or {})
    lead_name = customer_name or meta.get("lead_name", "")

    ghl = ghl_client or get_ghl_client()
    ghl_result = ghl.upsert_yelp_lead(
        name=str(lead_name or "Yelp Lead"),
        phone=phone_number,
        project_description=meta.get("project_description") or meta.get("service_type"),
        zip_code=conversation.zip_code or meta.get("zip_code"),
        existing_contact_id=meta.get("contact_check", {}).get("contact_id"),
    )

    takeover = human_takeover(
        db,
        conversation,
        reason="Phone collected — specialist taking over",
    )

    meta["phone_collected"] = True
    meta["customer_phone"] = phone_number
    if lead_name:
        meta["lead_name"] = lead_name
    if ghl_result.get("contact_id"):
        meta["ghl_contact_id"] = ghl_result["contact_id"]
    if ghl_result.get("opportunity_id"):
        meta["ghl_opportunity_id"] = ghl_result["opportunity_id"]
    meta["ghl_lead_status"] = ghl_result.get("status")
    conversation.metadata_ = meta
    conversation.outcome_detail = {"ghl": ghl_result, "phone": phone_number}
    conversation.completed_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.flush()

    return {
        "status": "phone_collected",
        "phone": phone_number,
        "ghl": ghl_result,
        "human_takeover": takeover,
        "message": (
            f"Phone collected. GHL lead synced. Specialist will call {phone_number} shortly."
        ),
    }


def human_takeover(
    db: Session,
    conversation: AIConversation,
    reason: str = "Manager joined the conversation",
) -> dict[str, Any]:
    conversation.ai_enabled = False
    conversation.state = "human_active"
    conversation.outcome = "handoff"
    db.add(conversation)
    db.flush()
    logger.info("HUMAN TAKEOVER: conversation=%s reason=%s", conversation.id, reason)
    return {
        "status": "human_takeover",
        "reason": reason,
        "message": "AI paused — human agent is handling this conversation.",
    }


def trigger_callback(
    phone: str,
    lead_name: str,
    context_summary: str,
    delay_seconds: int = 30,
) -> dict[str, Any]:
    """Phase 1 stub — logs intent; Retell integration comes later."""
    logger.info(
        "VOICE CALLBACK STUB: would call %s (%s) in %ss — %s",
        lead_name,
        phone,
        delay_seconds,
        context_summary,
    )
    return {
        "status": "scheduled_stub",
        "phone": phone,
        "lead_name": lead_name,
        "delay_seconds": delay_seconds,
        "message": (
            f"Callback to {lead_name} at {phone} queued (stub). "
            "Retell integration pending Phase 1."
        ),
    }


def escalate_to_human(reason: str, urgency: str = "normal") -> dict[str, Any]:
    logger.info("ESCALATE TO HUMAN: urgency=%s reason=%s", urgency, reason)
    return {
        "status": "escalated",
        "urgency": urgency,
        "reason": reason,
        "message": "A team member will follow up shortly.",
    }


def check_availability(zip_code: str, urgency: str = "flexible") -> dict[str, Any]:
    slots = [
        "Tomorrow 10:00 AM",
        "Tomorrow 2:00 PM",
        "Day after tomorrow 9:00 AM",
    ]
    if urgency == "emergency":
        slots.insert(0, "Today — emergency dispatch (call 213-566-8886)")
    return {
        "zip_code": zip_code,
        "available_slots": slots,
        "note": "Static slots for Phase 1 — HCP integration in Phase 2.",
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": (
                "Calculate price estimate for a glass service. "
                "Always call before quoting dollar amounts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {
                        "type": "string",
                        "description": "Service identifier from catalog",
                    },
                    "width_inches": {"type": "number"},
                    "height_inches": {"type": "number"},
                    "glass_type": {
                        "type": "string",
                        "enum": ["annealed", "tempered", "laminated", "low_e", "unknown"],
                    },
                    "zip_code": {"type": "string"},
                },
                "required": ["service_id", "zip_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_estimate",
            "description": "Book an in-home estimate appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "zip_code": {"type": "string"},
                    "service_id": {"type": "string"},
                    "preferred_datetime": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["contact_name", "phone", "zip_code", "service_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_phone",
            "description": (
                "Record the customer's phone number only after they explicitly share it "
                "in their message. Never use phone numbers from lead metadata or your "
                "first reply — wait for the customer to type their number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string"},
                    "customer_name": {"type": "string"},
                },
                "required": ["phone_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "human_takeover",
            "description": "Stop AI responses when a manager joins the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_callback",
            "description": (
                "Initiate AI voice callback to lead's phone in ~30 seconds. "
                "Only after explicit consent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "lead_name": {"type": "string"},
                    "context_summary": {"type": "string"},
                    "delay_seconds": {"type": "integer", "default": 30},
                },
                "required": ["phone", "lead_name", "context_summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Transfer conversation to human agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent", "emergency"],
                    },
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_existing_contact",
            "description": (
                "Check if lead already exists in CRM by phone (strong match) "
                "or Yelp name (weak match). Call before greeting when phone or name known."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check next available appointment slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {"type": "string"},
                    "urgency": {
                        "type": "string",
                        "enum": ["emergency", "this_week", "flexible"],
                    },
                },
                "required": ["zip_code"],
            },
        },
    },
]


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    kb: KnowledgeBase,
    db: Session,
    conversation: AIConversation,
    inbound_message: str | None = None,
    first_new_lead: bool = False,
) -> dict[str, Any]:
    if name == "get_price":
        result = get_price(kb, **args)
        if "price_min" in result:
            conversation.price_quoted_min = Decimal(str(result["price_min"]))
            conversation.price_quoted_max = Decimal(str(result["price_max"]))
            conversation.service_id = args.get("service_id")
            conversation.zip_code = args.get("zip_code")
        return result
    if name == "book_estimate":
        return book_estimate(db, conversation, **args)
    if name == "collect_phone":
        if not may_invoke_collect_phone(
            inbound_message=inbound_message,
            first_new_lead=first_new_lead,
        ):
            return {
                "status": "rejected",
                "error": "no_customer_phone_in_message",
                "message": (
                    "collect_phone blocked — customer has not shared their phone number "
                    "in a message yet. Keep asking for their number."
                ),
            }
        return collect_phone(db, conversation, **args)
    if name == "human_takeover":
        return human_takeover(db, conversation, **args)
    if name == "trigger_callback":
        conversation.consent_callback = True
        conversation.consent_callback_at = datetime.now(timezone.utc)
        conversation.state = "callback"
        return trigger_callback(**args)
    if name == "escalate_to_human":
        return human_takeover(db, conversation, reason=args.get("reason", "Escalated to human"))
    if name == "check_existing_contact":
        return check_existing_contact(
            args.get("phone"),
            args.get("name"),
        )
    if name == "check_availability":
        return check_availability(**args)
    return {"error": f"Unknown tool: {name}"}
