from __future__ import annotations

import logging
from typing import Any, Literal

from app.config import Settings, get_settings
from app.services.ghl import GHLClient, get_ghl_client, normalize_phone
from app.services.hcp import HCPClient, get_hcp_client

logger = logging.getLogger(__name__)

MatchConfidence = Literal["strong", "weak", "none"]


def check_existing_contact(
    phone: str | None = None,
    name: str | None = None,
    *,
    ghl_client: GHLClient | None = None,
    hcp_client: HCPClient | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Look up an existing CRM contact by phone (strong) or Yelp name (weak).

    Returns:
        exists, in_progress, owner, match_confidence, contact_id
    """
    settings = settings or get_settings()
    ghl = ghl_client or get_ghl_client(settings)
    hcp = hcp_client or get_hcp_client(settings)

    result: dict[str, Any] = {
        "exists": False,
        "in_progress": False,
        "owner": None,
        "match_confidence": "none",
        "contact_id": None,
        "hcp_match": False,
    }

    if phone and normalize_phone(phone):
        ghl_match = ghl.search_contact_by_phone(phone) if ghl.enabled else None
        hcp_match = hcp.search_customer_by_phone(phone) if hcp.enabled else None

        if ghl_match:
            result.update(
                {
                    "exists": True,
                    "in_progress": ghl_match.in_progress,
                    "owner": ghl_match.owner_name or ghl_match.assigned_to,
                    "match_confidence": "strong",
                    "contact_id": ghl_match.contact_id,
                }
            )
            return result

        if hcp_match:
            result.update(
                {
                    "exists": True,
                    "in_progress": False,
                    "owner": None,
                    "match_confidence": "strong",
                    "contact_id": None,
                    "hcp_match": True,
                    "hcp_customer_id": hcp_match.get("customer_id"),
                }
            )
            return result

    if name:
        ghl_match = ghl.search_contact_by_name(name) if ghl.enabled else None
        if ghl_match:
            result.update(
                {
                    "exists": True,
                    "in_progress": ghl_match.in_progress,
                    "owner": ghl_match.owner_name or ghl_match.assigned_to,
                    "match_confidence": "weak",
                    "contact_id": ghl_match.contact_id,
                }
            )
            return result

    return result
