"""Webhook response posting contract: should_post + messages[].

Zapier should only ever check `should_post` and post each item of `messages`
in order — no fragile multi-rule filters.
"""

from __future__ import annotations


def test_new_lead_should_post_two_messages(client):
    r = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": "sp_new_001",
            "consumer_name": "Victor M.",
            "project_description": "Shower door replacement",
            "zip_code": "90210",
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["should_post"] is True
    assert d["messages"] == [d["reply_text"], d["reply_text_2"]]
    assert len(d["messages"]) == 2


def test_follow_up_should_post_single_message(client):
    lead_id = "sp_fu_001"
    client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Sarah K.",
            "zip_code": "90210",
            "project_description": "Window repair",
        },
    )

    r = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "lead_id": lead_id,
            "consumer_message": "How much for a frameless shower door?",
            "user_type": "CONSUMER",
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["should_post"] is True
    assert d["messages"] == [d["reply_text"]]
    assert d["reply_text_2"] == ""


def test_business_message_should_not_post(client):
    r = client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_consumer_message",
            "lead_id": "sp_business_001",
            "consumer_message": "Our own AI reply",
            "user_type": "BUSINESS",
        },
    )
    assert r.status_code == 200
    d = r.json()
    assert d["should_post"] is False
    assert d["messages"] == []


def test_duplicate_message_should_not_post(client):
    lead_id = "sp_dup_001"
    client.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Nina",
            "zip_code": "90034",
        },
    )
    payload = {
        "lead_id": lead_id,
        "consumer_message": "What's the price?",
        "message_id": "sp_dup_msg",
        "user_type": "CONSUMER",
    }
    client.post("/api/v1/ai-responder/webhooks/zapier/yelp", json=payload)

    dup = client.post("/api/v1/ai-responder/webhooks/zapier/yelp", json=payload)
    assert dup.status_code == 200
    d = dup.json()
    assert d["state"] == "duplicate"
    assert d["should_post"] is False
    assert d["messages"] == []
