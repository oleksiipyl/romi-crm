from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_responder import AIConversation, AIMessage, LeadChannel
from app.services.state_machine import initial_state_for_event


def _first_present(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def normalize_yelp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map flexible Zapier/Yelp field names to unified lead format."""
    event_type = (
        _first_present(payload, "trigger", "event_type", "event", "type") or ""
    ).lower()

    lead_id = _first_present(payload, "lead_id", "id", "yelp_lead_id")
    name = _first_present(
        payload, "consumer_name", "name", "customer_name", "lead_name"
    )
    phone = _first_present(
        payload, "phone_number", "phone", "temporary_phone_number", "consumer_phone"
    )
    message = _first_present(
        payload,
        "message",
        "message_text",
        "consumer_message",
        "project_description",
        "description",
    )
    zip_code = _first_present(payload, "zip_code", "zip", "postal_code", "location_zip")
    service_type = _first_present(
        payload, "service_type", "category", "project_type", "job_type"
    )

    project_data = {
        k: v
        for k, v in payload.items()
        if k
        not in {
            "trigger",
            "event_type",
            "event",
            "type",
            "lead_id",
            "id",
            "consumer_name",
            "name",
            "phone_number",
            "phone",
            "message",
            "message_text",
        }
    }

    return {
        "event_type": event_type,
        "lead_id": lead_id,
        "name": name or "there",
        "phone": phone,
        "message": message,
        "zip_code": zip_code,
        "service_type": service_type,
        "project_data": project_data,
        "raw": payload,
    }


def _is_new_lead_event(event_type: str) -> bool:
    return any(
        token in event_type
        for token in ("new_lead", "new lead", "lead.created", "lead_created")
    )


def _is_message_event(event_type: str) -> bool:
    return any(
        token in event_type
        for token in ("message", "consumer_message", "new_consumer")
    )


def _is_phone_event(event_type: str) -> bool:
    return "phone" in event_type


def resolve_yelp_event_kind(
    event_type: str,
    *,
    is_new_conversation: bool,
    has_message: bool,
    has_phone: bool,
) -> str:
    """
    Classify ingest event: new_lead | message | phone | noop.

    Existing conversation + message text is always a continuation (message),
    even when Zapier omits trigger/event_type.
    """
    if _is_phone_event(event_type) and has_phone and not has_message:
        return "phone"

    if has_message and not is_new_conversation:
        return "message"

    if _is_message_event(event_type) and has_message:
        return "message"

    if is_new_conversation and (
        not event_type or _is_new_lead_event(event_type) or event_type == "yelp.new_lead"
    ):
        return "new_lead"

    if _is_new_lead_event(event_type) and is_new_conversation:
        return "new_lead"

    return "noop"


def get_or_create_conversation(
    db: Session,
    normalized: dict[str, Any],
    *,
    channel: str = "yelp_raq",
) -> tuple[AIConversation, bool]:
    external_id = normalized["lead_id"] or str(uuid.uuid4())
    existing = (
        db.query(AIConversation)
        .filter(
            AIConversation.channel == channel,
            AIConversation.channel_thread_id == external_id,
        )
        .first()
    )
    if existing:
        if normalized.get("phone"):
            meta = dict(existing.metadata_ or {})
            meta["phone"] = normalized["phone"]
            existing.metadata_ = meta
        if normalized.get("zip_code") and not existing.zip_code:
            existing.zip_code = normalized["zip_code"]
        db.add(existing)
        return existing, False

    contact_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    conversation = AIConversation(
        contact_id=contact_id,
        lead_id=lead_id,
        channel=channel,
        channel_thread_id=external_id,
        state=initial_state_for_event(is_new_lead=True, has_lead_reply=False),
        zip_code=normalized.get("zip_code"),
        metadata_={
            "lead_name": normalized.get("name"),
            "phone": normalized.get("phone"),
            "service_type": normalized.get("service_type"),
            "project_description": normalized.get("message"),
            "yelp_project": normalized.get("project_data"),
        },
    )
    db.add(conversation)
    db.flush()

    lead_channel = LeadChannel(
        lead_id=lead_id,
        contact_id=contact_id,
        channel=channel,
        external_id=external_id,
        project_data=normalized.get("project_data"),
        is_primary=True,
    )
    db.add(lead_channel)
    db.flush()
    return conversation, True


def record_inbound_message(
    db: Session,
    conversation: AIConversation,
    body: str,
    *,
    external_id: str | None = None,
    channel: str = "yelp_raq",
) -> AIMessage:
    if conversation.state == "greet":
        conversation.state = "qualify"

    msg = AIMessage(
        conversation_id=conversation.id,
        direction="inbound",
        sender_type="lead",
        channel=channel,
        content_type="text",
        body=body,
        external_id=external_id,
        conversation_state=conversation.state,
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    db.add(msg)
    db.flush()
    return msg


def record_outbound_message(
    db: Session,
    conversation: AIConversation,
    body: str,
    *,
    model: str | None = None,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    latency_ms: int | None = None,
    channel: str = "yelp_raq",
) -> AIMessage:
    now = datetime.now(timezone.utc)
    if not conversation.first_response_at:
        conversation.first_response_at = now
    conversation.last_message_at = now
    conversation.last_ai_message_at = now

    msg = AIMessage(
        conversation_id=conversation.id,
        direction="outbound",
        sender_type="ai",
        channel=channel,
        content_type="text",
        body=body,
        model=model,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
        conversation_state=conversation.state,
    )
    db.add(msg)
    db.flush()
    return msg


def record_tool_messages(
    db: Session,
    conversation: AIConversation,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
    channel: str = "yelp_raq",
) -> None:
    call_msg = AIMessage(
        conversation_id=conversation.id,
        direction="outbound",
        sender_type="ai",
        channel=channel,
        content_type="tool_call",
        tool_name=tool_name,
        tool_args=tool_args,
        conversation_state=conversation.state,
    )
    result_msg = AIMessage(
        conversation_id=conversation.id,
        direction="inbound",
        sender_type="system",
        channel=channel,
        content_type="tool_result",
        tool_name=tool_name,
        tool_result=tool_result,
        conversation_state=conversation.state,
    )
    db.add(call_msg)
    db.add(result_msg)
    db.flush()


def ingest_yelp_event(
    db: Session,
    payload: dict[str, Any],
) -> tuple[AIConversation, str | None, bool]:
    """
    Normalize Yelp/Zapier payload, upsert conversation, optionally record inbound.

    Returns (conversation, inbound_message_or_none, treat_as_new_lead).
    """
    normalized = normalize_yelp_payload(payload)
    event_type = normalized["event_type"]
    conversation, is_new_conversation = get_or_create_conversation(db, normalized)

    has_message = bool(normalized.get("message"))
    has_phone = bool(normalized.get("phone"))
    kind = resolve_yelp_event_kind(
        event_type,
        is_new_conversation=is_new_conversation,
        has_message=has_message,
        has_phone=has_phone,
    )

    if kind == "phone":
        if normalized.get("phone"):
            meta = dict(conversation.metadata_ or {})
            meta["phone"] = normalized["phone"]
            conversation.metadata_ = meta
            db.add(conversation)
        return conversation, None, False

    if kind == "message":
        inbound = normalized["message"]
        assert inbound is not None
        record_inbound_message(db, conversation, inbound)
        if normalized.get("phone"):
            meta = dict(conversation.metadata_ or {})
            meta["phone"] = normalized["phone"]
            conversation.metadata_ = meta
            db.add(conversation)
        return conversation, inbound, False

    if kind == "new_lead":
        if conversation.state == "idle":
            conversation.state = "greet"
        if normalized.get("phone"):
            meta = dict(conversation.metadata_ or {})
            meta["phone"] = normalized["phone"]
            conversation.metadata_ = meta
            db.add(conversation)
        return conversation, None, True

    # noop: duplicate new_lead webhook or metadata-only update on existing thread
    if normalized.get("phone"):
        meta = dict(conversation.metadata_ or {})
        meta["phone"] = normalized["phone"]
        conversation.metadata_ = meta
        db.add(conversation)
    return conversation, None, False
