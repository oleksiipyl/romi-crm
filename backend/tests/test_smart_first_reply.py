import json
from types import SimpleNamespace

from app.services.ai_brain import (
    AIBrain,
    BASE_PRICE_BLURB,
    FAST_GLASS_SERVICES_BLURB,
    has_raq_project_description,
)
from app.services.ingest import get_or_create_conversation
from app.services.state_machine import has_project_description, initial_state_for_event
from tests.conftest import MockMessage


def test_initial_state_qualify_when_project_description_present():
    assert (
        initial_state_for_event(
            is_new_lead=True,
            has_lead_reply=False,
            has_project_description=True,
        )
        == "qualify"
    )


def test_initial_state_greet_when_no_project_description():
    assert (
        initial_state_for_event(
            is_new_lead=True,
            has_lead_reply=False,
            has_project_description=False,
        )
        == "greet"
    )


def test_has_project_description_helper():
    assert has_project_description({"project_description": "Broken window"})
    assert not has_project_description({"project_description": ""})
    assert not has_project_description(None)


def test_first_turn_without_description_uses_ai_brain_fallback(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "smart_first_none_001",
            "name": "Alex",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert result["fallback"] is True
    assert conversation.metadata_["agent_name"] in result["reply_text"]
    assert "Fast Glass" in result["reply_text"]
    assert FAST_GLASS_SERVICES_BLURB in result["reply_text"]
    assert "$349" in result["reply_text"]
    assert "$625" in result["reply_text"]
    assert "$895" in result["reply_text"]
    assert "number" in result["reply_text"].lower() or "phone" in result["reply_text"].lower()
    assert "How can I help you" not in result["reply_text"]


def test_first_turn_with_description_uses_smart_fallback(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "smart_first_desc_001",
            "name": "Victor M.",
            "zip_code": "90034",
            "message": "Sliding patio door glass replacement",
        },
    )
    db_session.commit()

    assert has_raq_project_description(conversation)

    brain = AIBrain(kb=kb, settings=settings)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert result["fallback"] is True
    assert "Victor" in result["reply_text"] or "victor" in result["reply_text"].lower()
    assert conversation.metadata_["agent_name"] in result["reply_text"]
    assert "Fast Glass" in result["reply_text"]
    assert "number" in result["reply_text"].lower() or "phone" in result["reply_text"].lower()
    assert "$" in result["reply_text"]
    assert conversation.state == "qualify"
    assert "How can I help you" not in result["reply_text"]


def test_first_turn_with_description_uses_openai_brain(db_session, settings, kb):
    tool_call = SimpleNamespace(
        id="call_smart_001",
        function=SimpleNamespace(
            name="get_price",
            arguments=json.dumps(
                {"service_id": "sliding_door_glass", "zip_code": "90034"}
            ),
        ),
    )

    class SmartFirstClient:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, messages, tools):
            self.calls += 1
            system = next(m["content"] for m in messages if m["role"] == "system")
            user = next(
                m["content"]
                for m in messages
                if m["role"] == "user" and "New Yelp lead just arrived" in m["content"]
            )
            assert "project description" in user.lower()
            assert "get_price" in user
            assert "Robert" in system or "Olivia" in system or "Al" in system
            if self.calls == 1:
                return {
                    "message": MockMessage(content=None, tool_calls=[tool_call]),
                    "tokens_input": 100,
                    "tokens_output": 10,
                }
            return {
                "message": MockMessage(
                    content=(
                        "Hey Victor! Robert from Fast Glass — patio door glass is usually "
                        "$400-$900. What's the best number to reach you?"
                    )
                ),
                "tokens_input": 150,
                "tokens_output": 30,
            }

    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "smart_first_openai_001",
            "name": "Victor M.",
            "zip_code": "90034",
            "message": "Sliding patio door glass replacement",
        },
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Robert"
    conversation.metadata_ = meta
    db_session.commit()

    settings.openai_api_key = "test-key"
    client = SmartFirstClient()
    brain = AIBrain(kb=kb, settings=settings, client=client)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert result["fallback"] is False
    assert "get_price" in result.get("tools_called", [])
    assert client.calls >= 2
    assert "number" in result["reply_text"].lower()


def test_first_turn_without_description_uses_openai_brain(db_session, settings, kb):
    class NoDescriptionClient:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, messages, tools):
            self.calls += 1
            user = next(
                m["content"]
                for m in messages
                if m["role"] == "user" and "New Yelp lead just arrived" in m["content"]
            )
            assert "no project description" in user.lower()
            assert "$349" in user
            assert "$625" in user
            assert "$895" in user
            assert "shower doors" in user.lower()
            return {
                "message": MockMessage(
                    content=(
                        "Hey Alex! Olivia from Fast Glass — we do windows, storefronts, "
                        "shower doors, mirrors, and emergency board-ups. Single-pane starts "
                        "around $349+, double $625+, storefront $895+. What's the best "
                        "number to reach you?"
                    )
                ),
                "tokens_input": 120,
                "tokens_output": 40,
            }

    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "smart_first_openai_none_001",
            "name": "Alex",
            "zip_code": "90034",
        },
    )
    meta = dict(conversation.metadata_ or {})
    meta["agent_name"] = "Olivia"
    conversation.metadata_ = meta
    db_session.commit()

    settings.openai_api_key = "test-key"
    client = NoDescriptionClient()
    brain = AIBrain(kb=kb, settings=settings, client=client)
    result = brain.generate_reply(db_session, conversation, is_new_lead=True)

    assert result["fallback"] is False
    assert client.calls == 1
    assert "number" in result["reply_text"].lower()
    assert "How can I help you" not in result["reply_text"]
