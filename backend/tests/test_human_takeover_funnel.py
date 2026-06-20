from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest

from app.config import Settings
from app.services.contact_check import check_existing_contact
from app.services.ghl import GHLContactMatch
from app.services.ingest import get_or_create_conversation
from app.services.state_machine import apply_follow_up, build_follow_up_message
from app.services.takeover_funnel import evaluate_inbound_contact, evaluate_post_first_reply
from app.services.tools import collect_phone, execute_tool, human_takeover
from app.services.ai_brain import AIBrain


@pytest.fixture
def ghl_settings(settings: Settings) -> Settings:
    return Settings(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        zapier_webhook_secret=settings.zapier_webhook_secret,
        kb_path=settings.kb_path,
        app_env="test",
        ghl_api_token="test-ghl-token",
        ghl_location_id="zaegdQlLTbraKW5EzOKF",
        ghl_pipeline_id="OkNyO0uPN26HD0T8NmM4",
        ghl_pipeline_stage_id="d157a032-f0ce-44ca-9408-06f1a30994a7",
        ghl_yelp_source="YELP",
    )


class MockGHLClient:
    def __init__(self, *, phone_match=None, name_match=None):
        self.phone_match = phone_match
        self.name_match = name_match
        self.notes: list[tuple[str, str]] = []
        self.leads_created: list[dict] = []
        self.enabled = True

    def search_contact_by_phone(self, phone: str):
        return self.phone_match

    def search_contact_by_name(self, name: str):
        return self.name_match

    def notify_manager(self, message: str, *, contact_id=None, title="Yelp AI Responder"):
        if contact_id:
            self.notes.append((contact_id, message))
        return {"status": "notified", "note_added": bool(contact_id)}

    def add_contact_note(self, contact_id: str, body: str) -> bool:
        self.notes.append((contact_id, body))
        return True

    def upsert_yelp_lead(self, **kwargs):
        self.leads_created.append(kwargs)
        return {
            "status": "created",
            "contact_id": "ghl_contact_new_001",
            "opportunity_id": "ghl_opp_new_001",
        }

    def close(self):
        pass


def test_check_existing_contact_strong_in_progress(ghl_settings):
    mock = MockGHLClient(
        phone_match=GHLContactMatch(
            contact_id="ghl_001",
            name="Victor M.",
            phone="3105551234",
            assigned_to="user_42",
            status="Active",
            in_progress=True,
            owner_name="Alex",
        )
    )
    result = check_existing_contact(
        phone="310-555-1234",
        ghl_client=mock,  # type: ignore[arg-type]
        settings=ghl_settings,
    )
    assert result["exists"] is True
    assert result["in_progress"] is True
    assert result["match_confidence"] == "strong"
    assert result["contact_id"] == "ghl_001"
    assert result["owner"] == "Alex"


def test_check_existing_contact_weak_name_only(ghl_settings):
    mock = MockGHLClient(
        name_match=GHLContactMatch(
            contact_id="ghl_002",
            name="Sarah K.",
            phone=None,
            assigned_to=None,
            status=None,
            in_progress=False,
        )
    )
    result = check_existing_contact(
        name="Sarah K.",
        ghl_client=mock,  # type: ignore[arg-type]
        settings=ghl_settings,
    )
    assert result["exists"] is True
    assert result["match_confidence"] == "weak"
    assert result["in_progress"] is False


def test_check_existing_contact_none(ghl_settings):
    mock = MockGHLClient()
    result = check_existing_contact(
        phone="9999999999",
        name="Nobody",
        ghl_client=mock,  # type: ignore[arg-type]
        settings=ghl_settings,
    )
    assert result["match_confidence"] == "none"
    assert result["exists"] is False


def test_funnel_existing_in_progress_takeover_after_first(db_session, ghl_settings):
    mock = MockGHLClient(
        phone_match=GHLContactMatch(
            contact_id="ghl_inprog",
            name="Victor M.",
            phone="3105551234",
            assigned_to="user_1",
            status="Active",
            in_progress=True,
            owner_name="Manager",
        )
    )
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "funnel_inprog_001",
            "name": "Victor M.",
            "phone": "310-555-1234",
            "message": "Need window repair",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    decision = evaluate_post_first_reply(
        db_session,
        conversation,
        {"name": "Victor M.", "phone": "310-555-1234"},
        ghl_client=mock,  # type: ignore[arg-type]
    )
    db_session.commit()

    assert decision.action == "takeover_after_first"
    assert conversation.state == "human_active"
    assert conversation.ai_enabled is False
    assert mock.notes
    assert "существующего контакта" in mock.notes[0][1]


def test_funnel_existing_not_in_progress_takeover_after_first(db_session, ghl_settings):
    mock = MockGHLClient(
        phone_match=GHLContactMatch(
            contact_id="ghl_known",
            name="Lisa R.",
            phone="3105559999",
            assigned_to=None,
            status="Inactive",
            in_progress=False,
        )
    )
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "funnel_known_001",
            "name": "Lisa R.",
            "phone": "310-555-9999",
            "message": "Shower door quote",
        },
    )
    db_session.commit()

    decision = evaluate_post_first_reply(
        db_session,
        conversation,
        {"name": "Lisa R.", "phone": "310-555-9999"},
        ghl_client=mock,  # type: ignore[arg-type]
    )

    assert decision.action == "takeover_after_first"
    assert conversation.state == "human_active"
    assert any("Известный контакт" in note[1] for note in mock.notes)


def test_funnel_weak_match_takeover_after_first(db_session, ghl_settings):
    mock = MockGHLClient(
        name_match=GHLContactMatch(
            contact_id="ghl_weak",
            name="Chris P.",
            phone=None,
            assigned_to=None,
            status=None,
            in_progress=False,
        )
    )
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "funnel_weak_001", "name": "Chris P.", "message": "Mirror install"},
    )
    db_session.commit()

    decision = evaluate_post_first_reply(
        db_session,
        conversation,
        {"name": "Chris P."},
        ghl_client=mock,  # type: ignore[arg-type]
    )

    assert decision.action == "takeover_after_first"
    assert conversation.state == "human_active"
    assert any("Возможно существующий" in note[1] for note in mock.notes)


def test_funnel_none_sets_phone_first_from_next(db_session, ghl_settings):
    mock = MockGHLClient()
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "funnel_new_001", "name": "New Lead", "message": "Broken window"},
    )
    db_session.commit()

    decision = evaluate_post_first_reply(
        db_session,
        conversation,
        {"name": "New Lead"},
        ghl_client=mock,  # type: ignore[arg-type]
    )

    assert decision.action == "continue_ai"
    assert conversation.metadata_["phone_first_from_next"] is True
    assert not mock.notes


def test_post_first_reply_ghl_timeout_defers_without_error(db_session, ghl_settings):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "timeout_post_001",
            "name": "Timeout Lead",
            "phone": "310-555-0000",
            "message": "Window repair",
        },
    )
    db_session.commit()

    with patch(
        "app.services.takeover_funnel.check_existing_contact",
        side_effect=httpx.TimeoutException("GHL timed out"),
    ):
        decision = evaluate_post_first_reply(
            db_session,
            conversation,
            {"name": "Timeout Lead", "phone": "310-555-0000"},
        )

    assert decision.action == "continue_ai"
    assert decision.contact_check["timed_out"] is True
    assert decision.contact_check["defer_check"] is True
    assert conversation.metadata_["contact_check_pending"] is True
    assert conversation.state != "human_active"


def test_inbound_contact_ghl_timeout_defers_without_error(db_session, ghl_settings):
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "timeout_inbound_001",
            "name": "Follow-up Lead",
            "phone": "310-555-1111",
        },
    )
    db_session.commit()

    with patch(
        "app.services.takeover_funnel.check_existing_contact",
        side_effect=httpx.TimeoutException("GHL timed out"),
    ):
        decision = evaluate_inbound_contact(
            db_session,
            conversation,
            {"name": "Follow-up Lead", "phone": "310-555-1111"},
        )

    assert decision.action == "continue_ai"
    assert decision.contact_check["timed_out"] is True
    assert decision.contact_check["defer_check"] is True


def test_collect_phone_creates_ghl_lead_and_human_takeover(db_session, ghl_settings):
    mock = MockGHLClient()
    conversation, _ = get_or_create_conversation(
        db_session,
        {
            "lead_id": "collect_ghl_001",
            "name": "Tom B.",
            "zip_code": "90034",
            "message": "Storefront glass",
        },
    )
    meta = dict(conversation.metadata_ or {})
    meta["project_description"] = "Storefront glass"
    conversation.metadata_ = meta
    db_session.commit()

    result = collect_phone(
        db_session,
        conversation,
        phone_number="310-555-7777",
        customer_name="Tom B.",
        ghl_client=mock,  # type: ignore[arg-type]
    )
    db_session.commit()

    assert result["status"] == "phone_collected"
    assert conversation.metadata_["phone_collected"] is True
    assert conversation.state == "human_active"
    assert conversation.outcome == "handoff"
    assert len(mock.leads_created) == 1
    assert mock.leads_created[0]["phone"] == "310-555-7777"
    assert conversation.metadata_["ghl_contact_id"] == "ghl_contact_new_001"


def test_collect_phone_via_execute_tool(db_session, kb, ghl_settings):
    mock = MockGHLClient()
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "collect_tool_002", "name": "Amy"},
    )

    with patch("app.services.tools.get_ghl_client", return_value=mock):
        result = execute_tool(
            "collect_phone",
            {"phone_number": "+13105558888", "customer_name": "Amy"},
            kb=kb,
            db=db_session,
            conversation=conversation,
            inbound_message="Call me at 310-555-8888",
            first_new_lead=False,
        )

    assert result["status"] == "phone_collected"
    assert conversation.state == "human_active"
    assert mock.leads_created


def test_in_progress_contact_ai_stays_silent(db_session, settings, kb, ghl_settings):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "silent_001", "name": "Victor"},
    )
    human_takeover(db_session, conversation, reason="Existing in-progress contact")
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Hello?",
    )
    assert result.get("skipped") is True
    assert result["reply_text"] == ""


def test_abandon_follow_up_sends_presentation_then_abandoned(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "abandon_pres_001", "name": "Nina"},
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
    assert payload["final"] is True
    assert payload["presentation"] is True
    assert "Fast Glass" in payload["message"]
    assert "windows-glass-repair.olwininc.com" in payload["message"]
    assert "213-566-8886" in payload["message"]
    assert conversation.state == "abandoned"
    assert conversation.outcome == "abandoned"


def test_build_follow_up_third_is_presentation(db_session, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "build_pres_001", "name": "Nina"},
    )
    meta = dict(conversation.metadata_ or {})
    meta["follow_up_count"] = 2
    conversation.metadata_ = meta
    db_session.commit()

    message = build_follow_up_message(conversation)
    assert "Fast Glass" in message
    assert "windows-glass-repair.olwininc.com" in message


def test_webhook_business_user_still_skipped(client):
    response = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_consumer_message",
            "lead_id": "biz_skip_001",
            "consumer_message": "Our reply",
            "user_type": "BUSINESS",
        },
    )
    assert response.status_code == 200
    assert response.json()["state"] == "skipped"


def test_webhook_in_progress_gets_smart_first_then_takeover(client, db_session, ghl_settings):
    from app.models.ai_responder import AIConversation

    in_progress = GHLContactMatch(
        contact_id="ghl_webhook",
        name="Victor M.",
        phone="3105551234",
        assigned_to="mgr",
        status="Active",
        in_progress=True,
        owner_name="Alex",
    )
    mock = MockGHLClient(phone_match=in_progress)

    with patch("app.api.v1.ai_responder.get_ghl_client", return_value=mock):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "webhook_inprog_001",
                "consumer_name": "Victor M.",
                "phone_number": "310-555-1234",
                "project_description": "Window repair",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reply_text"]
    assert data["reply_text_2"]
    assert "Fast Glass" in data["reply_text"]
    assert "number" in data["reply_text"].lower() or "phone" in data["reply_text"].lower()
    assert "Window repair" in data["reply_text_2"] or "$" in data["reply_text_2"]

    conversation = (
        db_session.query(AIConversation)
        .filter(AIConversation.channel_thread_id == "webhook_inprog_001")
        .first()
    )
    db_session.expire_all()
    conversation = (
        db_session.query(AIConversation)
        .filter(AIConversation.channel_thread_id == "webhook_inprog_001")
        .first()
    )
    assert conversation is not None
    assert conversation.state == "human_active"
    assert conversation.ai_enabled is False


def test_webhook_consumer_new_lead_ai_first_reply(client):
    with patch("app.api.v1.ai_responder.get_ghl_client", return_value=MockGHLClient()):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "webhook_new_001",
                "consumer_name": "Fresh Lead",
                "zip_code": "90034",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reply_text"]
    assert data["reply_text_2"]
    assert "Fast Glass" in data["reply_text"]
    assert "number" in data["reply_text"].lower() or "phone" in data["reply_text"].lower()
    assert "How can I help you" not in data["reply_text"]
    assert data["state"] in {"greet", "qualify", "offer"}


def test_new_lead_no_typing_delay_on_first_reply(client):
    with (
        patch("app.api.v1.ai_responder.get_ghl_client", return_value=MockGHLClient()),
        patch("app.api.v1.ai_responder.simulate_typing_delay") as mock_delay,
    ):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "speed_new_001",
                "consumer_name": "Speed Test",
                "zip_code": "90034",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    mock_delay.assert_not_called()


def test_second_message_applies_typing_delay(client):
    lead_id = "speed_second_001"
    with patch("app.api.v1.ai_responder.get_ghl_client", return_value=MockGHLClient()):
        client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": lead_id,
                "consumer_name": "Speed Test 2",
                "zip_code": "90034",
                "user_type": "CONSUMER",
            },
        )

    with (
        patch("app.api.v1.ai_responder.get_ghl_client", return_value=MockGHLClient()),
        patch("app.api.v1.ai_responder.simulate_typing_delay") as mock_delay,
    ):
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_consumer_message",
                "lead_id": lead_id,
                "consumer_message": "How much for a window?",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    mock_delay.assert_called_once()


def test_ghl_check_runs_after_first_reply_not_before(client):
    from app.services.takeover_funnel import FunnelDecision

    with patch(
        "app.api.v1.ai_responder.evaluate_post_first_reply",
        return_value=FunnelDecision(action="continue_ai", contact_check={}),
    ) as mock_post:
        response = client.post(
            "/api/v1/ai-responder/webhooks/zapier/yelp",
            json={
                "trigger": "new_lead",
                "lead_id": "slow_ghl_001",
                "consumer_name": "Slow CRM",
                "phone_number": "310-555-0000",
                "user_type": "CONSUMER",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reply_text"]
    assert data["reply_text_2"]
    assert "Fast Glass" in data["reply_text"]
    assert "How can I help you" not in data["reply_text"]
    mock_post.assert_called_once()


def test_ai_first_then_phone_on_second(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "neutral_flow_001", "name": "Mike", "zip_code": "90001"},
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    r1 = brain.generate_reply(db_session, conversation, is_new_lead=True)
    assert "number" in r1["reply_text"].lower() or "phone" in r1["reply_text"].lower()
    assert r1["reply_text_2"]
    assert "How can I help you" not in r1["reply_text"]

    r2 = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="How much for a window?",
    )
    combined = r2["reply_text"].lower()
    assert "number" in combined or "phone" in combined or "reach you" in combined
