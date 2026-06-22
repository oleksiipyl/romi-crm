"""GHL API response parsing — regression tests for prod 500 on follow-up."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.ghl import GHLClient


@pytest.fixture
def ghl_settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        ghl_api_token="test-ghl-token",
        ghl_location_id="zaegdQlLTbraKW5EzOKF",
    )


class FakeResponse:
    def __init__(self, data, status_code: int = 200):
        self.status_code = status_code
        self._data = data
        self.content = b"{}"

    def json(self):
        return self._data


class FakeHTTP:
    def __init__(self, data):
        self._data = data

    def request(self, method, url, **kwargs):
        return FakeResponse(self._data)


def test_search_contact_by_name_skips_null_first_name_contacts(ghl_settings):
    """GHL may return contacts with firstName:null — must not crash the loop."""
    client = GHLClient(
        settings=ghl_settings,
        http_client=FakeHTTP(
            {
                "contacts": [
                    {"id": "bad", "firstName": None, "lastName": None},
                    {
                        "id": "good",
                        "name": "Alex P.",
                        "assignedTo": "user_1",
                    },
                ]
            }
        ),
    )
    match = client.search_contact_by_name("Alex")
    assert match is not None
    assert match.contact_id == "good"
    assert match.in_progress is True


def test_search_contact_by_phone_ignores_non_dict_contacts(ghl_settings):
    client = GHLClient(
        settings=ghl_settings,
        http_client=FakeHTTP(
            {
                "contacts": [
                    "not-a-dict",
                    {"id": "c1", "phone": "3105551234"},
                ]
            }
        ),
    )
    match = client.search_contact_by_phone("310-555-1234")
    assert match is not None
    assert match.contact_id == "c1"


def test_request_json_list_returns_empty_dict(ghl_settings):
    client = GHLClient(
        settings=ghl_settings,
        http_client=FakeHTTP([]),
    )
    data = client._request("GET", "/contacts/")
    assert data == {}
