import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ConversationState(str, enum.Enum):
    IDLE = "idle"
    GREET = "greet"
    QUALIFY = "qualify"
    OFFER = "offer"
    CLOSE = "close"
    CALLBACK = "callback"
    VOICE_ACTIVE = "voice_active"
    HUMAN_ACTIVE = "human_active"
    COMPLETE = "complete"
    RETRY_SMS = "retry_sms"
    FOLLOW_UP_QUEUED = "follow_up_queued"


class ConversationChannel(str, enum.Enum):
    YELP_RAQ = "yelp_raq"
    WEBSITE_WIDGET = "website_widget"
    SMS = "sms"
    VOICE = "voice"
    THUMBTACK = "thumbtack"
    GOOGLE_LSA = "google_lsa"


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Core CRM tables not yet migrated — store UUID without FK for now.
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    channel_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    state: Mapped[str] = mapped_column(String(30), nullable=False, default="greet")
    previous_state: Mapped[str | None] = mapped_column(String(30), nullable=True)

    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    service_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price_quoted_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_quoted_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    consent_callback: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ai_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)
    outcome_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_ai_conversations_channel", "channel", "channel_thread_id"),
        Index("idx_ai_conversations_contact", "contact_id"),
        Index("idx_ai_conversations_lead", "lead_id"),
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversation_state: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["AIConversation"] = relationship(
        "AIConversation", back_populates="messages"
    )

    __table_args__ = (
        Index("idx_ai_messages_conversation", "conversation_id", "created_at"),
    )


class LeadChannel(Base):
    __tablename__ = "lead_channels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_lead_channels_lead", "lead_id"),
        Index("idx_lead_channels_external", "channel", "external_id", unique=True),
    )


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="json_import")
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    service_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("idx_kb_documents_category", "category"),)
