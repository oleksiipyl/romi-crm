from datetime import datetime, timedelta, timezone

from app.services.ai_brain import AIBrain
from app.services.ingest import get_or_create_conversation
from app.services.state_machine import (
    apply_client_signal,
    build_client_signal_reply,
    detect_client_signal,
    should_send_follow_up,
    should_skip_ai_reply,
)


def test_detect_client_signal_stop():
    assert detect_client_signal("Please stop messaging me") == "stop"
    assert detect_client_signal("I'm not interested") == "stop"


def test_detect_client_signal_already_booked():
    assert detect_client_signal("We already found someone for the job") == "already_booked"
    assert detect_client_signal("Already ordered from another company") == "already_booked"


def test_detect_client_signal_aggressive():
    assert detect_client_signal("This is a scam, stop harassing me") == "stop"
    assert detect_client_signal("You people are useless idiots") == "aggressive"


def test_build_client_signal_replies():
    assert "won't message again" in build_client_signal_reply("stop", name="Alex", company_phone="213-772-6882")
    assert "Glad you got it sorted" in build_client_signal_reply(
        "already_booked", name="Alex", company_phone="213-772-6882"
    )
    assert "213-772-6882" in build_client_signal_reply(
        "aggressive", name="Alex", company_phone="213-772-6882"
    )


def test_stop_signal_disables_ai_and_blocks_followups(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "stop_signal_001", "name": "Chris"},
    )
    db_session.commit()

    reply = apply_client_signal(
        db_session,
        conversation,
        "stop",
        company_phone="213-772-6882",
    )

    assert "won't message again" in reply
    assert conversation.state == "abandoned"
    assert conversation.ai_enabled is False
    assert conversation.metadata_["messaging_opt_out"] is True
    assert should_skip_ai_reply(conversation)
    assert should_send_follow_up(conversation) is False


def test_already_booked_sets_complete(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "booked_signal_001", "name": "Nina"},
    )
    db_session.commit()

    reply = apply_client_signal(
        db_session,
        conversation,
        "already_booked",
        company_phone="213-772-6882",
    )

    assert conversation.state == "complete"
    assert conversation.outcome == "already_booked"
    assert conversation.ai_enabled is True
    assert "Glad you got it sorted" in reply
    assert should_skip_ai_reply(conversation)
    assert should_send_follow_up(conversation) is False


def test_aggressive_sets_abandoned_with_business_phone(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "aggressive_signal_001", "name": "Pat"},
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    brain.generate_reply(db_session, conversation, is_new_lead=True)
    db_session.commit()

    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="You guys are a scam, this is terrible",
    )

    assert result["client_signal"] == "aggressive"
    assert "213-772-6882" in result["reply_text"]
    assert conversation.state == "abandoned"
    assert should_send_follow_up(conversation) is False

    follow_up = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Hello?",
    )
    assert follow_up.get("skipped") is True


def test_brain_stop_signal_blocks_future_replies(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "stop_brain_001", "name": "Sam"},
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    brain.generate_reply(db_session, conversation, is_new_lead=True)
    db_session.commit()

    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Stop texting me, not interested",
    )

    assert result["client_signal"] == "stop"
    assert conversation.ai_enabled is False
    assert conversation.state == "abandoned"

    again = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="Are you there?",
    )
    assert again.get("skipped") is True


def test_brain_already_booked_farewell(db_session, settings, kb):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "booked_brain_001", "name": "Lisa"},
    )
    db_session.commit()

    brain = AIBrain(kb=kb, settings=settings)
    brain.generate_reply(db_session, conversation, is_new_lead=True)
    db_session.commit()

    result = brain.generate_reply(
        db_session,
        conversation,
        inbound_message="We already hired someone else",
    )

    assert result["client_signal"] == "already_booked"
    assert conversation.state == "complete"
    assert "Glad you got it sorted" in result["reply_text"]


def test_follow_up_not_sent_after_opt_out(db_session):
    conversation, _ = get_or_create_conversation(
        db_session,
        {"lead_id": "followup_stop_001", "name": "Nina"},
    )
    now = datetime.now(timezone.utc)
    conversation.first_response_at = now - timedelta(hours=30)
    conversation.last_ai_message_at = now - timedelta(hours=30)
    conversation.last_message_at = now - timedelta(hours=30)
    db_session.commit()

    apply_client_signal(
        db_session,
        conversation,
        "stop",
        company_phone="213-772-6882",
    )
    db_session.commit()

    assert should_send_follow_up(conversation, now) is False
