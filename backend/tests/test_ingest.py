from app.services.ingest import ingest_yelp_event, normalize_yelp_payload, resolve_yelp_event_kind


def test_normalize_yelp_payload_no_default_new_lead():
    normalized = normalize_yelp_payload({"lead_id": "abc", "consumer_message": "hello"})
    assert normalized["event_type"] == ""
    assert normalized["message"] == "hello"


def test_normalize_yelp_payload_yelp_zapier_field_names():
    normalized = normalize_yelp_payload(
        {
            "lead_id": "yelp_001",
            "consumer_name": "Robert",
            "Project Additional Info": "Shower door cracked",
            "Project Job Names": "Shower Door Installation",
            "Location Postal Code": "90211",
        }
    )
    assert normalized["message"] == "Shower door cracked"
    assert normalized["service_type"] == "Shower Door Installation"
    assert normalized["zip_code"] == "90211"


def test_resolve_existing_conversation_with_message_is_continuation():
    kind = resolve_yelp_event_kind(
        "",
        is_new_conversation=False,
        has_message=True,
        has_phone=False,
    )
    assert kind == "message"


def test_resolve_new_conversation_without_trigger_is_new_lead():
    kind = resolve_yelp_event_kind(
        "",
        is_new_conversation=True,
        has_message=False,
        has_phone=False,
    )
    assert kind == "new_lead"


def test_ingest_second_message_without_trigger_records_inbound(db_session):
    lead_id = "ingest_multi_001"
    ingest_yelp_event(
        db_session,
        {
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Victor M.",
            "project_description": "Sliding patio door glass",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    conversation, inbound, treat_as_new_lead, is_duplicate = ingest_yelp_event(
        db_session,
        {
            "lead_id": lead_id,
            "consumer_message": "My phone is 310-555-1234, please call me",
        },
    )

    assert treat_as_new_lead is False
    assert is_duplicate is False
    assert inbound == "My phone is 310-555-1234, please call me"
    assert conversation.state in {"qualify", "offer", "greet", "callback", "human_active"}

    from app.models.ai_responder import AIMessage

    inbound_msgs = (
        db_session.query(AIMessage)
        .filter(
            AIMessage.conversation_id == conversation.id,
            AIMessage.direction == "inbound",
        )
        .all()
    )
    assert len(inbound_msgs) == 1
    assert "310-555-1234" in inbound_msgs[0].body


def test_ingest_duplicate_message_id_skips(db_session):
    lead_id = "ingest_dedup_msgid_001"
    ingest_yelp_event(
        db_session,
        {
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Victor M.",
            "zip_code": "90034",
        },
    )
    db_session.commit()

    conversation, inbound, treat_as_new_lead, is_duplicate = ingest_yelp_event(
        db_session,
        {
            "lead_id": lead_id,
            "consumer_message": "How much for a window?",
            "message_id": "yelp_msg_001",
        },
    )
    db_session.commit()
    assert is_duplicate is False
    assert inbound == "How much for a window?"

    conversation2, inbound2, _, is_duplicate2 = ingest_yelp_event(
        db_session,
        {
            "lead_id": lead_id,
            "consumer_message": "How much for a window?",
            "message_id": "yelp_msg_001",
        },
    )
    assert conversation2.id == conversation.id
    assert is_duplicate2 is True

    from app.models.ai_responder import AIMessage

    inbound_msgs = (
        db_session.query(AIMessage)
        .filter(
            AIMessage.conversation_id == conversation.id,
            AIMessage.direction == "inbound",
        )
        .all()
    )
    assert len(inbound_msgs) == 1


def test_ingest_duplicate_text_within_60_seconds_skips(db_session):
    lead_id = "ingest_dedup_text_001"
    ingest_yelp_event(
        db_session,
        {
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Sarah K.",
            "zip_code": "90210",
        },
    )
    db_session.commit()

    message = "Can you call me today?"
    conversation, _, _, is_duplicate = ingest_yelp_event(
        db_session,
        {"lead_id": lead_id, "consumer_message": message},
    )
    db_session.commit()
    assert is_duplicate is False

    conversation2, _, _, is_duplicate2 = ingest_yelp_event(
        db_session,
        {"lead_id": lead_id, "consumer_message": message},
    )
    assert conversation2.id == conversation.id
    assert is_duplicate2 is True

    from app.models.ai_responder import AIMessage

    inbound_msgs = (
        db_session.query(AIMessage)
        .filter(
            AIMessage.conversation_id == conversation.id,
            AIMessage.direction == "inbound",
        )
        .all()
    )
    assert len(inbound_msgs) == 1
