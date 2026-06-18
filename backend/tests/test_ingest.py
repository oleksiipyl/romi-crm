from app.services.ingest import ingest_yelp_event, normalize_yelp_payload, resolve_yelp_event_kind


def test_normalize_yelp_payload_no_default_new_lead():
    normalized = normalize_yelp_payload({"lead_id": "abc", "consumer_message": "hello"})
    assert normalized["event_type"] == ""
    assert normalized["message"] == "hello"


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

    conversation, inbound, treat_as_new_lead = ingest_yelp_event(
        db_session,
        {
            "lead_id": lead_id,
            "consumer_message": "My phone is 310-555-1234, please call me",
        },
    )

    assert treat_as_new_lead is False
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
