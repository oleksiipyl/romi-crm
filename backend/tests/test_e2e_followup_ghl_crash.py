"""End-to-end regression for the prod 500 on Yelp follow-up.

Drives the full ASGI stack (webhook -> ingest -> takeover_funnel -> real
GHLClient parsing -> ai_brain) using a fake HTTP transport that mimics the
GoHighLevel response that crashed production: a contact row with
``firstName: null`` returned when searching by the lead name ("Alex").
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.ai_brain import AIBrain, get_ai_brain
from app.services.ghl import GHLClient
from tests.conftest import MockChatClient


class _FakeResponse:
    def __init__(self, data, status_code: int = 200):
        self.status_code = status_code
        self._data = data
        self.content = b"{}"

    def json(self):
        return self._data


class _CrashyGHLHTTP:
    """Returns a contact list containing a null-name row (prod crash trigger)."""

    def request(self, method, url, **kwargs):
        if "/contacts" in url:
            return _FakeResponse(
                {
                    "contacts": [
                        {"id": "null_row", "firstName": None, "lastName": None},
                        {
                            "id": "alex_owner",
                            "name": "Alex",
                            "assignedTo": "owner_user",
                            "status": "Active",
                        },
                    ]
                }
            )
        return _FakeResponse({})

    def close(self):
        pass


@pytest.fixture
def prod_like_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    settings = Settings(
        database_url="sqlite://",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        zapier_webhook_secret="",
        kb_path="data/fast_glass_kb.json",
        app_env="production",
        ghl_api_token="prod-token",
        ghl_location_id="loc-123",
    )
    brain = AIBrain(settings=settings, client=MockChatClient())

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_brain] = lambda: brain

    def fake_get_ghl_client(*_args, **_kwargs):
        return GHLClient(settings=settings, http_client=_CrashyGHLHTTP())

    with (
        patch("app.api.v1.ai_responder.get_ghl_client", fake_get_ghl_client),
        patch("app.services.takeover_funnel.get_ghl_client", fake_get_ghl_client),
        patch("app.api.v1.ai_responder.asyncio.sleep", return_value=None),
    ):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


def test_followup_with_null_name_ghl_contact_no_500(prod_like_app):
    lead_id = "e2e_alex_null_name_001"

    r1 = prod_like_app.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "trigger": "new_lead",
            "lead_id": lead_id,
            "consumer_name": "Alex",
            "project_description": "door glass services",
            "zip_code": "90211",
        },
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["reply_text"]

    r2 = prod_like_app.post(
        "/api/v1/ai-responder/webhooks/zapier/yelp",
        json={
            "lead_id": lead_id,
            "consumer_name": "Alex",
            "message": "Could you provide a quote please?",
            "user_type": "CONSUMER",
            "message_id": f"m_{lead_id}_1",
        },
    )
    # Before the fix this returned HTTP 500 (TypeError on None + str).
    assert r2.status_code == 200, r2.text
    assert r2.json()["conversation_id"] == r1.json()["conversation_id"]
