from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ZapierYelpWebhookRequest(BaseModel):
    """Flexible Zapier/Yelp payload — accepts known and extra fields."""

    trigger: str | None = None
    event_type: str | None = None
    event: str | None = None
    type: str | None = None
    lead_id: str | None = None
    id: str | None = None
    consumer_name: str | None = None
    name: str | None = None
    phone_number: str | None = None
    phone: str | None = None
    message: str | None = None
    message_text: str | None = None
    consumer_message: str | None = None
    project_description: str | None = None
    zip_code: str | None = None
    service_type: str | None = None

    model_config = {"extra": "allow"}

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class WebhookResponse(BaseModel):
    status: str = "ok"
    conversation_id: UUID
    reply_text: str
    state: str
    event_type: str | None = None
    fallback: bool = False
    tools_called: list[str] = Field(default_factory=list)


class TwilioSmsWebhookRequest(BaseModel):
    MessageSid: str | None = None
    From: str | None = None
    To: str | None = None
    Body: str | None = None

    model_config = {"extra": "allow"}


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
