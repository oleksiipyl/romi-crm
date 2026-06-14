"""AI Lead Responder core tables

Revision ID: 001_ai_responder
Revises:
Create Date: 2026-06-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_ai_responder"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("channel_thread_id", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False, server_default="greet"),
        sa.Column("previous_state", sa.String(length=30), nullable=True),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column("service_id", sa.String(length=100), nullable=True),
        sa.Column("price_quoted_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_quoted_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("consent_callback", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("consent_callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ai_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=30), nullable=True),
        sa.Column("outcome_detail", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_conversations_channel", "ai_conversations", ["channel", "channel_thread_id"])
    op.create_index("idx_ai_conversations_contact", "ai_conversations", ["contact_id"])
    op.create_index("idx_ai_conversations_lead", "ai_conversations", ["lead_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("sender_type", sa.String(length=10), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("tool_args", sa.JSON(), nullable=True),
        sa.Column("tool_result", sa.JSON(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("conversation_state", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_messages_conversation", "ai_messages", ["conversation_id", "created_at"])

    op.create_table(
        "lead_channels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("project_data", sa.JSON(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "external_id", name="uq_lead_channels_channel_external"),
    )
    op.create_index("idx_lead_channels_lead", "lead_channels", ["lead_id"])
    op.create_index("idx_lead_channels_external", "lead_channels", ["channel", "external_id"])

    op.create_table(
        "kb_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="json_import"),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("content_raw", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("service_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_kb_documents_category", "kb_documents", ["category"])


def downgrade() -> None:
    op.drop_index("idx_kb_documents_category", table_name="kb_documents")
    op.drop_table("kb_documents")
    op.drop_index("idx_lead_channels_external", table_name="lead_channels")
    op.drop_index("idx_lead_channels_lead", table_name="lead_channels")
    op.drop_table("lead_channels")
    op.drop_index("idx_ai_messages_conversation", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("idx_ai_conversations_lead", table_name="ai_conversations")
    op.drop_index("idx_ai_conversations_contact", table_name="ai_conversations")
    op.drop_index("idx_ai_conversations_channel", table_name="ai_conversations")
    op.drop_table("ai_conversations")
