import uuid
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.models.ai_responder import AIConversation, AIMessage, LeadChannel
from app.services.ai_brain import AIBrain


def test_zapier_yelp_new_lead_returns_reply(client, db_session):
    payload = {
        "trigger": "new_lead",
        "lead_id": "yelp_test_lead_001",
        "consumer_name": "Victor M.",
        "phone_number": "+13105551234",
        "project_description": "Sliding patio door glass replacement, 6ft x 8ft",
        "zip_code": "90034",
        "service_type": "Door Installation",
    }

    response = client.post("/api/v1/ai-responder/webhooks/zapier/yelp", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["reply_text"]
    assert "Victor" in data["reply_text"] or "patio" in data["reply_text"].lower()
    assert data["state"] in {"greet", "qualify", "offer"}
    assert data["fallback"] is True  # no API key in tests

    conversation = db_session.get(AIConversation, uuid.UUID(data["conversation_id"]))
    assert conversation is not None
    assert conversation.channel == "yelp_raq"
    assert conversation.channel_thread_id == "yelp_test_lead_001"
    assert conversation.metadata_["lead_name"] == "Victor M."

    lead_channel = (
        db_session.query(LeadChannel)
        .filter(LeadChannel.external_id == "yelp_test_lead_001")
        .first()
    )
    assert lead_channel is not None

    messages = (
        db_session.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation.id)
        .all()
    )
    assert len(messages) >= 1
    assert any(m.sender_type == "ai" for m in messages)


def test_zapier_yelp_follow_up_message(client, db_session):
    lead_id = "yelp_test_lead_002"
    client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Sarah K.",
            "zip_code": "90210",
            "project_description": "Shower door replacement",
        },
    )

    response = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_consumer_message",
            "lead_id": lead_id,
            "consumer_message": "How much for a frameless shower door?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reply_text"]

    messages = (
        db_session.query(AIMessage)
        .filter(AIMessage.conversation_id == uuid.UUID(data["conversation_id"]))
        .all()
    )
    assert any(m.direction == "inbound" for m in messages)
    assert sum(1 for m in messages if m.sender_type == "ai") >= 2


def test_zapier_webhook_secret_rejected(db_engine, settings: Settings):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.db.session import get_db
    from app.main import app
    from app.services.ai_brain import get_ai_brain

    secret_settings = Settings(
        database_url="sqlite://",
        zapier_webhook_secret="secret123",
        kb_path=settings.kb_path,
    )
    TestingSession = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = lambda: secret_settings
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_brain] = lambda: AIBrain(settings=secret_settings)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={"lead_id": "x", "consumer_name": "Test"},
        )
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_zapier_webhook_applies_typing_delay(client):
    with (
        patch(
            "app.api.v1.ai_responder.random.uniform",
            return_value=5.5,
        ) as mock_uniform,
        patch(
            "app.api.v1.ai_responder.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep,
    ):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "delay_test_001",
                "consumer_name": "Delay Test",
                "zip_code": "90034",
                "project_description": "Window repair",
            },
        )

    assert response.status_code == 200
    mock_uniform.assert_called_once_with(4.0, 8.0)
    mock_sleep.assert_awaited_once_with(5.5)
