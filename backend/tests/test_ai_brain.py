import json
from types import SimpleNamespace

import pytest

from app.models.ai_responder import AIConversation
from app.services.ai_brain import AIBrain
from app.services.ingest import get_or_create_conversation
from app.services.tools import book_estimate, execute_tool, get_price, trigger_callback


def test_get_price_from_kb(kb):
    result = get_price(kb, service_id="sliding_door_glass", zip_code="90034")
    assert result["service_name"] == "Sliding Door Glass Replacement"
    assert result["price_min"] >= 350
    assert result["price_max"] <= 2000
    assert result["in_service_zone"] is True


def test_get_price_with_dimensions(kb):
    result = get_price(
        kb,
        service_id="double_pane_window",
        zip_code="90024",
        width_inches=36,
        height_inches=48,
        glass_type="tempered",
    )
    assert result["price_min"] > 250
    assert "tempered" not in result.get("error", "")


def test_trigger_callback_stub(caplog):
    result = trigger_callback(
        phone="+13105551234",
        lead_name="Victor",
        context_summary="Patio door quote",
        delay_seconds=30,
    )
    assert result["status"] == "scheduled_stub"
    assert "VOICE CALLBACK STUB" in caplog.text


def test_book_estimate_updates_conversation(db_session, kb):
    normalized = {
        "lead_id": "book_test_001",
        "name": "Mike T.",
        "phone": "+13105559999",
        "zip_code": "90066",
        "message": "Mirror installation",
    }
    conversation, _ = get_or_create_conversation(db_session, normalized)
    db_session.commit()

    result = book_estimate(
        db_session,
        conversation,
        contact_name="Mike T.",
        phone="+13105559999",
        zip_code="90066",
        service_id="wall_mirror",
        preferred_datetime="2026-06-20T14:00:00",
    )
    db_session.commit()

    assert result["status"] == "scheduled"
    assert conversation.state == "complete"
    assert conversation.outcome == "booked"


def test_ai_brain_with_mock_openai(db_session, settings, kb, mock_chat_client):
    normalized = {
        "lead_id": "brain_test_001",
        "name": "Victor M.",
        "zip_code": "90034",
        "message": "Sliding door glass",
    }
    conversation, _ = get_or_create_conversation(db_session, normalized)
    db_session.commit()

    settings.openai_api_key = "test-key"
    brain = AIBrain(kb=kb, settings=settings, client=mock_chat_client)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert result["reply_text"]
    assert result["fallback"] is False
    assert "Victor" in result["reply_text"] or "patio" in result["reply_text"].lower()


def test_ai_brain_tool_call_flow(db_session, settings, kb):
    tool_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(
            name="get_price",
            arguments=json.dumps(
                {"service_id": "shower_door_glass", "zip_code": "90210"}
            ),
        ),
    )

    class ToolThenReplyClient:
        def __init__(self):
            self.step = 0

        def generate(self, messages, tools):
            self.step += 1
            if self.step == 1:
                return {
                    "message": MockMessage(content=None, tool_calls=[tool_call]),
                    "tokens_input": 200,
                    "tokens_output": 10,
                }
            return {
                "message": MockMessage(
                    content="Shower doors run $450-$1,200. Want a callback in 30 seconds?"
                ),
                "tokens_input": 250,
                "tokens_output": 30,
            }

    class MockMessage:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    normalized = {
        "lead_id": "brain_tool_001",
        "name": "Lisa R.",
        "zip_code": "90210",
    }
    conversation, _ = get_or_create_conversation(db_session, normalized)
    conversation.state = "qualify"
    db_session.commit()

    settings.openai_api_key = "test-key"
    brain = AIBrain(kb=kb, settings=settings, client=ToolThenReplyClient())
    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="How much for a shower door?",
    )

    assert "450" in result["reply_text"] or "1,200" in result["reply_text"]
    assert "get_price" in result.get("tools_called", [])
    assert conversation.price_quoted_min is not None


def test_execute_tool_get_price(db_session, kb):
    normalized = {"lead_id": "tool_001", "name": "Test", "zip_code": "90001"}
    conversation, _ = get_or_create_conversation(db_session, normalized)
    result = execute_tool(
        "get_price",
        {"service_id": "emergency_board_up", "zip_code": "90001"},
        kb=kb,
        db=db_session,
        conversation=conversation,
    )
    assert result["price_min"] == 299  # Updated 2026-06-14: real HCP median for emergency board-up ($450 median, $299 min)
    assert conversation.service_id == "emergency_board_up"
