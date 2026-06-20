import asyncio
import logging
import random
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import SessionLocal, get_db
from app.models.ai_responder import AIConversation
from app.schemas.ai_responder import (
    HealthResponse,
    TwilioSmsWebhookRequest,
    WebhookResponse,
    ZapierYelpWebhookRequest,
)
from app.services.ai_brain import AIBrain, get_ai_brain, is_first_ai_turn
from app.services.ghl import get_ghl_client
from app.services.ingest import (
    get_or_create_conversation,
    ingest_yelp_event,
    normalize_yelp_payload,
    record_inbound_message,
)
from app.services.takeover_funnel import evaluate_inbound_contact, evaluate_post_first_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-responder", tags=["ai-responder"])

TYPING_DELAY_MIN_SECONDS = 4.0
TYPING_DELAY_MAX_SECONDS = 8.0


async def simulate_typing_delay() -> float:
    """Pause before returning a reply so responses feel human-typed."""
    delay = random.uniform(TYPING_DELAY_MIN_SECONDS, TYPING_DELAY_MAX_SECONDS)
    await asyncio.sleep(delay)
    return delay


def run_post_first_reply_background(
    conversation_id: str,
    normalized: dict[str, Any],
) -> None:
    """CRM lookup after neutral first reply — must not block HTTP response."""
    db = SessionLocal()
    try:
        conversation = db.get(AIConversation, uuid.UUID(conversation_id))
        if conversation is None:
            return
        ghl_client = get_ghl_client()
        try:
            evaluate_post_first_reply(
                db,
                conversation,
                normalized,
                ghl_client=ghl_client,
            )
            db.commit()
        finally:
            ghl_client.close()
    except Exception:
        logger.exception(
            "Post-first-reply contact check failed for conversation %s",
            conversation_id,
        )
    finally:
        db.close()


def _verify_zapier_secret(
    settings: Settings = Depends(get_settings),
    x_webhook_secret: str | None = Header(default=None),
) -> None:
    if settings.zapier_webhook_secret:
        if x_webhook_secret != settings.zapier_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post(
    "/webhooks/zapier/yelp",
    response_model=WebhookResponse,
    dependencies=[Depends(_verify_zapier_secret)],
)
async def zapier_yelp_webhook(
    payload: ZapierYelpWebhookRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    brain: AIBrain = Depends(get_ai_brain),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    """
    Ingest Yelp lead/message from Zapier, run AI brain, return reply text.

    Zapier uses the reply_text in a follow-up action (Create Message on Yelp).
    """
    # Ignore messages from BUSINESS (our own replies) — prevent infinite loop
    if payload.user_type and payload.user_type.upper() != "CONSUMER":
        logger.info("Skipping non-CONSUMER message (user_type=%s)", payload.user_type)
        return WebhookResponse(
            conversation_id="skipped",
            reply_text="",
            reply_text_2="",
            state="skipped",
            event_type=None,
            fallback=False,
            tools_called=[],
        )

    raw = payload.to_payload()
    normalized = normalize_yelp_payload(raw)
    conversation, inbound, treat_as_new_lead, is_duplicate = ingest_yelp_event(db, raw)
    db.commit()

    if is_duplicate:
        return WebhookResponse(
            conversation_id=str(conversation.id),
            reply_text="",
            reply_text_2="",
            state="duplicate",
            event_type=normalized.get("event_type"),
            fallback=False,
            tools_called=[],
        )

    was_first_turn = is_first_ai_turn(db, conversation)

    if not was_first_turn:
        ghl_client = get_ghl_client()
        try:
            funnel = evaluate_inbound_contact(
                db,
                conversation,
                normalized,
                ghl_client=ghl_client,
            )
            db.commit()
            if funnel.action == "skip_ai":
                return WebhookResponse(
                    conversation_id=str(conversation.id),
                    reply_text="",
                    reply_text_2="",
                    state=conversation.state,
                    event_type=normalized.get("event_type"),
                    fallback=False,
                    tools_called=["human_takeover"],
                )
        finally:
            ghl_client.close()

    result = brain.generate_reply(
        db,
        conversation,
        is_new_lead=treat_as_new_lead,
        inbound_message=inbound,
    )

    if was_first_turn:
        if settings.app_env == "test" or settings.database_url.startswith("sqlite"):
            ghl_client = get_ghl_client()
            try:
                evaluate_post_first_reply(
                    db,
                    conversation,
                    normalized,
                    ghl_client=ghl_client,
                )
                db.commit()
            finally:
                ghl_client.close()
        else:
            background_tasks.add_task(
                run_post_first_reply_background,
                str(conversation.id),
                normalized,
            )

    if not treat_as_new_lead:
        await simulate_typing_delay()

    return WebhookResponse(
        conversation_id=str(conversation.id),
        reply_text=result["reply_text"],
        reply_text_2=result.get("reply_text_2", ""),
        state=result["state"],
        event_type=normalized.get("event_type"),
        fallback=result.get("fallback", False),
        tools_called=result.get("tools_called", []),
    )


@router.post("/webhooks/twilio/sms", response_model=WebhookResponse)
async def twilio_sms_webhook(
    request: Request,
    db: Session = Depends(get_db),
    brain: AIBrain = Depends(get_ai_brain),
) -> WebhookResponse:
    """
    Twilio SMS inbound stub — accepts form-encoded or JSON payload.
    Phase 1 prep: store message, run brain, return reply (Twilio TwiML later).
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    sms = TwilioSmsWebhookRequest.model_validate(data)
    if not sms.From or not sms.Body:
        raise HTTPException(status_code=400, detail="Missing From or Body")

    thread_id = sms.From
    normalized = {
        "lead_id": thread_id,
        "name": "SMS Lead",
        "phone": sms.From,
        "message": sms.Body,
        "trigger": "twilio.sms",
    }
    conversation, is_new = get_or_create_conversation(
        db,
        {**normalized, "event_type": "twilio.sms"},
        channel="sms",
    )
    record_inbound_message(
        db,
        conversation,
        sms.Body,
        external_id=sms.MessageSid,
        channel="sms",
    )
    db.commit()

    result = brain.generate_reply(
        db,
        conversation,
        is_new_lead=is_new,
        inbound_message=sms.Body,
    )

    return WebhookResponse(
        conversation_id=str(conversation.id),
        reply_text=result["reply_text"],
        reply_text_2=result.get("reply_text_2", ""),
        state=result["state"],
        event_type="twilio.sms",
        fallback=result.get("fallback", False),
        tools_called=result.get("tools_called", []),
    )
