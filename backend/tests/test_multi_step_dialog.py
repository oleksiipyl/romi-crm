import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.db.session import get_db
from app.main import app
from app.services.ai_brain import AIBrain
from tests.conftest import MockChatClient, MockMessage


class MultiStepMockClient:
    """Returns greet+price on turn 1, contextual phone ack on turn 2."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages, tools):
        self.calls += 1
        user_texts = [
            m["content"]
            for m in messages
            if m.get("role") == "user" and "New Yelp lead just arrived" not in m.get("content", "")
        ]
        is_new_lead_prompt = any(
            "New Yelp lead just arrived" in m.get("content", "") for m in messages if m.get("role") == "user"
        )

        if is_new_lead_prompt and not user_texts:
            return {
                "message": MockMessage(
                    content=(
                        "Hi Victor! This is Olivia from Fast Glass & Windows — I saw your "
                        "patio door request. What's the best number to reach you for a quick call?"
                    )
                ),
                "tokens_input": 100,
                "tokens_output": 40,
            }

        if user_texts and any("310" in t for t in user_texts):
            return {
                "message": MockMessage(
                    content=(
                        "Perfect Victor! Got your number — our specialist will call you within "
                        "30 minutes about the patio door."
                    )
                ),
                "tokens_input": 180,
                "tokens_output": 35,
            }

        pytest.fail(f"Unexpected dialog state on call {self.calls}: {messages}")


@pytest.fixture
def multi_step_client(db_engine, settings: Settings, kb):
    brain = AIBrain(
        kb=kb,
        settings=Settings(**{**settings.model_dump(), "openai_api_key": "test-key"}),
        client=MultiStepMockClient(),
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    from app.services.ai_brain import get_ai_brain

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_brain] = lambda: brain

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_multi_step_dialog_remembers_context(multi_step_client):
    lead_id = "multi_step_victor_001"

    r1 = multi_step_client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Victor M.",
            "project_description": "Sliding patio door glass replacement",
            "zip_code": "90034",
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert "650" in d1["reply_text"] or "Victor" in d1["reply_text"] or "number" in d1["reply_text"].lower()
    assert d1["state"] in {"greet", "qualify", "offer"}

  # Zapier follow-up WITHOUT trigger — reproduces live bug
    r2 = multi_step_client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "lead_id": lead_id,
            "consumer_message": "Yes, my phone is 310-555-9999, please call me",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d1["conversation_id"] == d2["conversation_id"]

    reply = d2["reply_text"].lower()
    assert "how can we help with your glass needs today" not in reply
    assert "thanks" in reply or "got your number" in reply or "perfect" in reply or "30 minutes" in reply
    assert d2["state"] in {"qualify", "offer", "callback", "human_active", "greet"}


def test_multi_step_dialog_fallback_without_openai(client, db_session):
    """Fallback path must not re-greet on second message (no API key in default client)."""
    lead_id = "multi_step_fallback_002"

    r1 = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Sarah K.",
            "project_description": "Shower door replacement",
            "zip_code": "90210",
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "lead_id": lead_id,
            "consumer_message": "My phone is 310-555-4444, call me please",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert "how can we help with your glass needs today" not in d2["reply_text"].lower()
    assert (
        "thanks" in d2["reply_text"].lower()
        or "got your number" in d2["reply_text"].lower()
        or "perfect" in d2["reply_text"].lower()
    )

    from app.models.ai_responder import AIMessage

    msgs = (
        db_session.query(AIMessage)
        .filter(AIMessage.conversation_id == uuid.UUID(d2["conversation_id"]))
        .order_by(AIMessage.created_at)
        .all()
    )
    assert sum(1 for m in msgs if m.direction == "inbound") == 1
    assert sum(1 for m in msgs if m.sender_type == "ai") == 2
