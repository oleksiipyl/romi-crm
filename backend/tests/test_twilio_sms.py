import uuid

from app.models.ai_responder import AIConversation, AIMessage


def test_twilio_sms_webhook_stub(client, db_session):
    response = client.post(
        "/api/v1/ai-responder/webhooks/twilio/sms",
        data={
            "MessageSid": "SM123",
            "From": "+13105551234",
            "To": "+12135668886",
            "Body": "I need my window fixed ASAP",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["reply_text"]
    assert data["event_type"] == "twilio.sms"

    conversation = db_session.get(AIConversation, uuid.UUID(data["conversation_id"]))
    assert conversation.channel == "sms"
    messages = (
        db_session.query(AIMessage)
        .filter(AIMessage.conversation_id == conversation.id)
        .all()
    )
    assert any(m.direction == "inbound" and m.body == "I need my window fixed ASAP" for m in messages)


def test_twilio_sms_missing_body_returns_400(client):
    response = client.post(
        "/api/v1/ai-responder/webhooks/twilio/sms",
        data={"From": "+13105551234"},
    )
    assert response.status_code == 400
