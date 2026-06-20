import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models.ai_responder import AIConversation
from app.services.ai_brain import AIBrain
from app.services.ingest import get_or_create_conversation
from app.services.personas import AGENT_PERSONAS, assign_agent_name
from app.services.state_machine import (
    apply_follow_up,
    build_follow_up_message,
    should_send_follow_up,
)
from app.services.tools import collect_phone, execute_tool, human_takeover
from tests.conftest import MockMessage


def test_new_conversation_assigns_agent_persona(db_session):
    conversation, is_new = get_or_create_conversation(
        db_session,
        {
            "lead_id": "persona_test_001",
            "name": "Victor M.",
            "zip_code": "90034",
            "message": "Broken window",
        },
    )
    assert is_new is True
    assert conversation.metadata_["agent_name"] in AGENT_PERSONAS


@pytest.mark.parametrize("agent_name", AGENT_PERSONAS)
def test_all_three_personas_can_be_assigned(agent_name):
    with patch("app.services.personas.random.choice", return_value=agent_name):
        assert assign_agent_name() == agent_name


@pytest.mark.parametrize("agent_name", AGENT_PERSONAS)
def test_fallback_first_reply_introduces_persona_and_services(
    db_session, settings, kb, agent_name
):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": f"persona_test_{agent_name.lower()}",
            "name": "Sarah K.",
            "zip_code": "90210",
        },
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = agent_name
    conversation.metadata_ = meta
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    reply = result["reply_text"]
    assert agent_name in reply
    assert "Fast Glass" in reply
    assert "number" in reply.lower() or "phone" in reply.lower()
    assert "AI" not in reply
    assert "assistant" not in reply.lower()
    assert "How can I help you" not in reply
    assert result["reply_text_2"]
    assert "shower doors" in result["reply_text_2"].lower()
    assert "$349" in result["reply_text_2"]


def test_fallback_bot_question_denies_bot_identity(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "bot_check_001", "name": "Chris", "zip_code": "90034"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Olivia"
    conversation.metadata_ = meta
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    brain.generate_reply(db_session, conversation, is_new_lead=True)
    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Are you a bot?",
    )

    reply = result["reply_text"]
    assert "real person" in reply.lower()
    assert "AI" not in reply
    assert "bot" not in reply.lower()
    assert "assistant" not in reply.lower()


def test_fallback_asks_for_phone_within_first_messages(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "phone_ask_001", "name": "Mike", "zip_code": "90001"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Robert"
    conversation.metadata_ = meta
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    r1 = brain.generate_reply(db_session, conversation, is_new_lead=True)
    r2 = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="How much for a window?",
    )

    assert "number" in r1["reply_text"].lower() or "phone" in r1["reply_text"].lower()
    assert r1["reply_text_2"]
    combined = r2["reply_text"].lower()
    assert "number" in combined or "phone" in combined or "reach you" in combined


def test_collect_phone_sets_outcome(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "collect_phone_001", "name": "Lisa R."},
    )
    result = collect_phone(
        db_session,
        conversation,
        phone_number="310-555-1234",
        customer_name="Lisa R.",
    )
    db_session.commit()

    assert result["status"] == "phone_collected"
    assert conversation.metadata_["phone_collected"] is True
    assert conversation.metadata_["customer_phone"] == "310-555-1234"
    assert conversation.state == "human_active"
    assert conversation.outcome == "handoff"


def test_execute_tool_collect_phone(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "collect_tool_001", "name": "Tom"},
    )
    result = execute_tool(
        "collect_phone",
        {"phone_number": "+13105551234", "customer_name": "Tom"},
        kb=kb,
        db=db_session,
        conversation=conversation,
        inbound_message="You can reach me at 310-555-1234",
        first_new_lead=False,
    )
    assert result["status"] == "phone_collected"
    assert conversation.state == "human_active"
    assert conversation.outcome == "handoff"


def test_human_takeover_stops_ai(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "takeover_001", "name": "Alex"},
    )
    human_takeover(db_session, conversation, reason="Manager joined")
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Are you still there?",
    )

    assert result.get("skipped") is True
    assert conversation.ai_enabled is False
    assert conversation.state == "human_active"


def test_follow_up_schedule_and_abandon(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "followup_001", "name": "Nina"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Robert"
    conversation.metadata_ = meta
    now = datetime.now(timezone.utc)
    conversation.first_response_at = now - timedelta(hours=25)
    conversation.last_ai_message_at = now - timedelta(hours=25)
    conversation.last_message_at = now - timedelta(hours=25)
    db_session.commit()

    assert should_send_follow_up(conversation, now) is True

    payload = apply_follow_up(conversation, now)
    assert payload is not None
    assert payload["follow_up_number"] == 1
    assert "Robert" in payload["message"]
    assert conversation.metadata_["follow_up_count"] == 1


def test_follow_up_abandoned_after_three_attempts(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "followup_002", "name": "Nina"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Olivia"
    meta["follow_up_count"] = 2
    meta["last_follow_up_at"] = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
    conversation.metadata_ = meta
    now = datetime.now(timezone.utc)
    conversation.last_ai_message_at = now - timedelta(hours=49)
    conversation.last_message_at = now - timedelta(hours=49)
    db_session.commit()

    payload = apply_follow_up(conversation, now)
    assert payload is not None
    assert payload["follow_up_number"] == 3
    assert payload["final"] is True
    assert "Fast Glass" in payload["message"]
    assert conversation.state == "abandoned"
    assert conversation.ai_enabled is False


def test_openai_mock_introduces_as_persona(db_session, settings, kb):
    class PersonaClient:
        def generate(self, messages, tools):
            system = next(m["content"] for m in messages if m["role"] == "system")
            assert any(persona in system for persona in AGENT_PERSONAS)
            assert "AI assistant" not in system
            assert "Never say AI" in system or "Never say AI, bot" in system
            return {
                "message": MockMessage(
                    content=(
                        "Hi Victor! Robert here from Fast Glass. "
                        "What's the best number to reach you?"
                    )
                ),
                "tokens_input": 50,
                "tokens_output": 20,
            }

    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "openai_persona_001", "name": "Victor", "zip_code": "90034"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Robert"
    conversation.metadata_ = meta
    db_session.commit()

    settings.openai_api_key = "test-key"
    brain = AIBrain(kb=kb, settings=settings, client=PersonaClient())
    first = brain.generate_reply(db_session, conversation, is_new_lead=True)
    assert "Robert" in first["reply_text"]
    assert "number" in first["reply_text"].lower()
    assert first["reply_text_2"]

    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="I need help with my window",
    )

    assert "Robert" in result["reply_text"]
    assert "number" in result["reply_text"].lower()
