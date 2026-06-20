from unittest.mock import patch

from app.services.ai_brain import AIBrain
from app.services.ghl import ensure_early_yelp_contact
from app.services.ingest import get_or_create_conversation
from app.services.takeover_funnel import evaluate_post_first_reply
from tests.test_human_takeover_funnel import MockGHLClient


def test_kb_company_phone(kb):
    assert kb.company_phone() == "213-772-6882"


def test_fallback_cta_after_two_phone_asks(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "cta_test_001", "name": "Mike", "zip_code": "90001"},
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)

    brain.generate_reply(db_session, conversation, is_new_lead=True)
    db_session.commit()
    assert conversation.metadata_["phone_ask_count"] == 1

    r2 = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="How much for a window?",
    )
    db_session.commit()
    assert conversation.metadata_["phone_ask_count"] == 2
    assert "213-772-6882" not in r2["reply_text"]

    r3 = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Still thinking about it",
    )
    assert "No worries! Call us at 213-772-6882" in r3["reply_text"]
    assert "drop your number here" in r3["reply_text"].lower()


def test_ensure_early_yelp_contact_creates_contact(db_session):
    mock = MockGHLClient()
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "early_ghl_001",
            "name": "Victor M.",
            "zip_code": "90034",
            "message": "Broken window",
        },
    )
    db_session.commit()

    result = ensure_early_yelp_contact(db_session, conversation, ghl_client=mock)  # type: ignore[arg-type]

    assert result["status"] == "created"
    assert result["contact_id"] == "ghl_early_contact_001"
    assert conversation.metadata_["ghl_early_contact_id"] == "ghl_early_contact_001"
    assert len(mock.early_contacts_created) == 1
    created = mock.early_contacts_created[0]
    assert created["name"] == "Victor M."
    assert created["lead_id"] == "early_ghl_001"
    assert created["zip_code"] == "90034"
    assert created["channel"] == "yelp"

    again = ensure_early_yelp_contact(db_session, conversation, ghl_client=mock)  # type: ignore[arg-type]
    assert again["status"] == "exists"
    assert len(mock.early_contacts_created) == 1


def test_post_first_reply_creates_early_ghl_contact(db_session):
    mock = MockGHLClient()
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "early_funnel_001",
            "name": "Sarah K.",
            "zip_code": "90210",
        },
    )
    db_session.commit()

    evaluate_post_first_reply(
        db_session,
        conversation,
        {"name": "Sarah K.", "lead_id": "early_funnel_001", "zip_code": "90210"},
        ghl_client=mock,  # type: ignore[arg-type]
    )

    assert conversation.metadata_["ghl_early_contact_id"] == "ghl_early_contact_001"
    assert mock.early_contacts_created[0]["lead_id"] == "early_funnel_001"


def test_webhook_first_lead_creates_early_ghl_contact(client, db_session):
    mock = MockGHLClient()
    with patch("app.api.v1.ai_responder.get_ghl_client", return_value=mock):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "webhook_early_ghl_001",
                "consumer_name": "Fresh Lead",
                "zip_code": "90034",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    assert len(mock.early_contacts_created) == 1
    assert mock.early_contacts_created[0]["name"] == "Fresh Lead"
    assert mock.early_contacts_created[0]["lead_id"] == "webhook_early_ghl_001"
    assert mock.early_contacts_created[0]["zip_code"] == "90034"
    assert mock.early_contacts_created[0]["channel"] == "yelp"

    from app.models.ai_responder import AIConversation

    conversation = (
        db_session.query(AIConversation)
        .filter(AIConversation.channel_thread_id == "webhook_early_ghl_001")
        .first()
    )
    assert conversation.metadata_["ghl_early_contact_id"] == "ghl_early_contact_001"
