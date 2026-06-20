import json
from types import SimpleNamespace

from app.services.ai_brain import AIBrain
from app.services.ingest import get_or_create_conversation
from app.services.tools import (
    execute_tool,
    may_invoke_collect_phone,
    message_contains_phone,
)
from tests.conftest import MockMessage


def test_message_contains_phone():
    assert message_contains_phone("Call me at 310-555-1234")
    assert not message_contains_phone("What's the price?")
    assert not message_contains_phone(None)


def test_may_invoke_collect_phone_rules():
    assert not may_invoke_collect_phone(inbound_message=None, first_new_lead=True)
    assert not may_invoke_collect_phone(
        inbound_message="310-555-1234",
        first_new_lead=True,
    )
    assert not may_invoke_collect_phone(
        inbound_message="How much for a window?",
        first_new_lead=False,
    )
    assert may_invoke_collect_phone(
        inbound_message="My number is 310-555-9999",
        first_new_lead=False,
    )


def test_execute_tool_rejects_collect_phone_without_customer_message(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "guard_no_msg_001",
            "name": "Amy",
            "phone": "3105551234",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    result = execute_tool(
        "collect_phone",
        {"phone_number": "310-555-1234", "customer_name": "Amy"},
        kb=kb,
        db=db_session,
        conversation=conversation,
    )

    assert result["status"] == "rejected"
    assert conversation.state != "human_active"
    assert not conversation.metadata_.get("phone_collected")


def test_execute_tool_rejects_collect_phone_on_first_new_lead(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "guard_first_001",
            "name": "Amy",
            "phone": "3105551234",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    result = execute_tool(
        "collect_phone",
        {"phone_number": "310-555-1234", "customer_name": "Amy"},
        kb=kb,
        db=db_session,
        conversation=conversation,
        inbound_message="My number is 310-555-1234",
        first_new_lead=True,
    )

    assert result["status"] == "rejected"
    assert conversation.state != "human_active"


def test_execute_tool_allows_collect_phone_when_message_has_digits(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "guard_ok_001", "name": "Amy", "zip_code": "90034"},
    )
    db_session.commit()

    result = execute_tool(
        "collect_phone",
        {"phone_number": "310-555-7777", "customer_name": "Amy"},
        kb=kb,
        db=db_session,
        conversation=conversation,
        inbound_message="Sure, call me at 310-555-7777",
        first_new_lead=False,
    )

    assert result["status"] == "phone_collected"
    assert conversation.state == "human_active"
    assert conversation.metadata_["phone_collected"] is True


def test_first_smart_reply_blocks_collect_phone_tool(db_session, settings, kb):
    tool_call = SimpleNamespace(
        id="call_collect_early",
        function=SimpleNamespace(
            name="collect_phone",
            arguments=json.dumps(
                {"phone_number": "310-555-1234", "customer_name": "Victor"}
            ),
        ),
    )

    class EarlyCollectClient:
        def generate(self, messages, tools):
            return {
                "message": MockMessage(content=None, tool_calls=[tool_call]),
                "tokens_input": 50,
                "tokens_output": 10,
            }

    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "guard_brain_first_001",
            "name": "Victor",
            "phone": "3105551234",
            "zip_code": "90034",
            "message": "Broken window",
        },
    )
    db_session.commit()

    settings.openai_api_key = "test-key"
    brain = AIBrain(kb=kb, settings=settings, client=EarlyCollectClient())
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert "collect_phone" not in result.get("tools_called", [])
    assert conversation.state in {"qualify", "offer", "greet"}
    assert conversation.ai_enabled is True
    assert not conversation.metadata_.get("phone_collected")


def test_follow_up_collects_phone_when_client_sends_number(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "guard_followup_001",
            "name": "Victor",
            "phone": "3105551234",
            "zip_code": "90034",
            "message": "Broken window",
        },
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    brain.generate_reply(db_session, conversation, is_new_lead=True)

    result = execute_tool(
        "collect_phone",
        {"phone_number": "310-555-4444", "customer_name": "Victor"},
        kb=kb,
        db=db_session,
        conversation=conversation,
        inbound_message="My phone is 310-555-4444, please call",
        first_new_lead=False,
    )

    assert result["status"] == "phone_collected"
    assert conversation.state == "human_active"
