from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.ai_responder import AIConversation

logger = logging.getLogger(__name__)

GHL_BASE_URL = "https://services.leadconnectorhq.com"
GHL_API_VERSION = "2021-07-28"
GHL_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

OPEN_OPPORTUNITY_STATUSES = {"open", "active", "in_progress", "new", "pending"}


@dataclass
class GHLContactMatch:
    contact_id: str
    name: str
    phone: str | None
    assigned_to: str | None
    status: str | None
    in_progress: bool
    owner_name: str | None = None


class HTTPClient(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


def normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.strip().split()).lower()


class GHLClient:
    def __init__(
        self,
        settings: Settings | None = None,
        http_client: HTTPClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = http_client
        self._owns_client = http_client is None

    @property
    def enabled(self) -> bool:
        return bool(self.settings.ghl_api_token and self.settings.ghl_location_id)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.ghl_api_token}",
            "Version": GHL_API_VERSION,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": GHL_BROWSER_USER_AGENT,
        }

    def _client(self) -> HTTPClient:
        if self._http is None:
            timeout = self.settings.ghl_lookup_timeout_seconds
            self._http = httpx.Client(timeout=timeout)
        return self._http

    def close(self) -> None:
        if self._owns_client and self._http is not None:
            close = getattr(self._http, "close", None)
            if callable(close):
                close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.enabled:
            return {}
        url = f"{GHL_BASE_URL}{path}"
        response = self._client().request(method, url, headers=self._headers(), **kwargs)
        if response.status_code >= 400:
            logger.warning(
                "GHL API error %s %s: %s",
                method,
                path,
                getattr(response, "text", response),
            )
            return {}
        if not getattr(response, "content", b""):
            return {}
        return response.json()

    def search_contact_by_phone(self, phone: str) -> GHLContactMatch | None:
        digits = normalize_phone(phone)
        if not digits:
            return None

        data = self._request(
            "GET",
            "/contacts/",
            params={
                "locationId": self.settings.ghl_location_id,
                "query": digits,
                "limit": 5,
            },
        )
        contacts = data.get("contacts") or []
        for contact in contacts:
            contact_phone = normalize_phone(contact.get("phone"))
            if contact_phone and contact_phone == digits:
                return self._to_match(contact)
        return None

    def search_contact_by_name(self, name: str) -> GHLContactMatch | None:
        clean = name.strip()
        if not clean or clean.lower() in {"there", "sms lead", "unknown"}:
            return None

        data = self._request(
            "GET",
            "/contacts/",
            params={
                "locationId": self.settings.ghl_location_id,
                "query": clean,
                "limit": 5,
            },
        )
        contacts = data.get("contacts") or []
        target = normalize_name(clean)
        for contact in contacts:
            contact_name = normalize_name(
                contact.get("name")
                or contact.get("firstName", "")
                + " "
                + contact.get("lastName", "")
            )
            if contact_name and (
                contact_name == target
                or target in contact_name
                or contact_name in target
            ):
                return self._to_match(contact)
        return None

    def _to_match(self, contact: dict[str, Any]) -> GHLContactMatch:
        contact_id = str(contact.get("id") or contact.get("contactId") or "")
        assigned_to = contact.get("assignedTo") or contact.get("ownerId")
        status = (contact.get("status") or contact.get("contactStatus") or "").strip()
        owner_name = contact.get("ownerName") or contact.get("assignedToName")
        in_progress = self._contact_in_progress(contact_id, assigned_to, status)
        display_name = (
            contact.get("name")
            or f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
            or "Unknown"
        )
        return GHLContactMatch(
            contact_id=contact_id,
            name=display_name,
            phone=contact.get("phone"),
            assigned_to=str(assigned_to) if assigned_to else None,
            status=status or None,
            in_progress=in_progress,
            owner_name=owner_name,
        )

    def _contact_in_progress(
        self,
        contact_id: str,
        assigned_to: str | None,
        status: str | None,
    ) -> bool:
        if assigned_to:
            return True
        if status and status.lower() in {"active", "in progress", "in_progress"}:
            return True
        if contact_id and self._has_open_opportunity(contact_id):
            return True
        return False

    def _has_open_opportunity(self, contact_id: str) -> bool:
        data = self._request(
            "GET",
            "/opportunities/search",
            params={
                "location_id": self.settings.ghl_location_id,
                "contact_id": contact_id,
                "limit": 10,
            },
        )
        opportunities = data.get("opportunities") or data.get("data") or []
        for opp in opportunities:
            status = str(opp.get("status") or opp.get("pipelineStageName") or "").lower()
            if not status or status in OPEN_OPPORTUNITY_STATUSES:
                return True
            if status not in {"won", "lost", "closed", "abandoned"}:
                return True
        return False

    def add_contact_note(self, contact_id: str, body: str) -> bool:
        if not contact_id:
            return False
        result = self._request(
            "POST",
            f"/contacts/{contact_id}/notes",
            json={"body": body},
        )
        return bool(result)

    def notify_manager(
        self,
        message: str,
        *,
        contact_id: str | None = None,
        title: str = "Yelp AI Responder",
    ) -> dict[str, Any]:
        """Notify manager via contact note (reliable) and log internal alert."""
        logger.info("GHL MANAGER NOTIFY: %s", message)
        note_ok = False
        if contact_id:
            note_ok = self.add_contact_note(
                contact_id,
                f"[{title}] {message}",
            )
        return {
            "status": "notified" if note_ok else "logged",
            "message": message,
            "contact_id": contact_id,
            "note_added": note_ok,
        }

    def upsert_yelp_lead(
        self,
        *,
        name: str,
        phone: str,
        project_description: str | None = None,
        zip_code: str | None = None,
        existing_contact_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update GHL contact + Yelp opportunity."""
        if not self.enabled:
            return {"status": "skipped", "reason": "GHL not configured"}

        contact_id = existing_contact_id
        if not contact_id:
            existing = self.search_contact_by_phone(phone)
            contact_id = existing.contact_id if existing else None

        if contact_id:
            self._request(
                "PUT",
                f"/contacts/{contact_id}",
                json={
                    "phone": phone,
                    "name": name,
                    "source": self.settings.ghl_yelp_source,
                    "tags": ["yelp", "ai-responder"],
                },
            )
        else:
            created = self._request(
                "POST",
                "/contacts/",
                json={
                    "locationId": self.settings.ghl_location_id,
                    "name": name,
                    "phone": phone,
                    "source": self.settings.ghl_yelp_source,
                    "tags": ["yelp", "ai-responder"],
                },
            )
            contact_id = str(created.get("contact", {}).get("id") or created.get("id") or "")

        if not contact_id:
            return {"status": "error", "reason": "Failed to create GHL contact"}

        opportunity_name = project_description or "Yelp lead"
        opp = self._request(
            "POST",
            "/opportunities/",
            json={
                "locationId": self.settings.ghl_location_id,
                "contactId": contact_id,
                "name": opportunity_name[:100],
                "pipelineId": self.settings.ghl_pipeline_id,
                "pipelineStageId": self.settings.ghl_pipeline_stage_id,
                "source": self.settings.ghl_yelp_source,
                "status": "open",
            },
        )
        opportunity_id = str(
            opp.get("opportunity", {}).get("id") or opp.get("id") or ""
        )

        note = (
            f"Yelp lead — phone collected via AI responder. "
            f"Project: {project_description or 'n/a'}. ZIP: {zip_code or 'n/a'}."
        )
        self.add_contact_note(contact_id, note)

        return {
            "status": "created",
            "contact_id": contact_id,
            "opportunity_id": opportunity_id,
        }

    def create_early_yelp_contact(
        self,
        *,
        name: str,
        lead_id: str,
        zip_code: str | None = None,
        channel: str = "yelp",
        project_description: str | None = None,
    ) -> dict[str, Any]:
        """Create a GHL contact when a Yelp lead first arrives (before phone collection)."""
        if not self.enabled:
            return {"status": "skipped", "reason": "GHL not configured"}

        body: dict[str, Any] = {
            "locationId": self.settings.ghl_location_id,
            "name": name,
            "source": self.settings.ghl_yelp_source,
            "tags": ["yelp", "ai-responder", "early-lead", f"lead:{lead_id}"],
        }
        if zip_code:
            body["postalCode"] = zip_code

        created = self._request("POST", "/contacts/", json=body)
        contact_id = str(created.get("contact", {}).get("id") or created.get("id") or "")
        if not contact_id:
            return {"status": "error", "reason": "Failed to create GHL contact"}

        note = (
            f"Yelp early lead. Lead ID: {lead_id}. Channel: {channel}. "
            f"ZIP: {zip_code or 'n/a'}. Project: {project_description or 'n/a'}."
        )
        self.add_contact_note(contact_id, note)
        return {"status": "created", "contact_id": contact_id}


def ensure_early_yelp_contact(
    db: Session,
    conversation: AIConversation,
    *,
    ghl_client: GHLClient | None = None,
) -> dict[str, Any]:
    """Idempotently create a GHL contact on first Yelp lead arrival."""
    meta = dict(conversation.metadata_ or {})
    existing = meta.get("ghl_early_contact_id") or meta.get("ghl_contact_id")
    if existing:
        return {"status": "exists", "contact_id": existing}

    if conversation.channel != "yelp_raq":
        return {"status": "skipped", "reason": "not_yelp_channel"}

    ghl = ghl_client or get_ghl_client()
    result = ghl.create_early_yelp_contact(
        name=str(meta.get("lead_name") or "Yelp Lead"),
        lead_id=conversation.channel_thread_id,
        zip_code=conversation.zip_code or meta.get("zip_code"),
        channel="yelp",
        project_description=meta.get("project_description") or meta.get("service_type"),
    )
    if result.get("contact_id"):
        meta["ghl_early_contact_id"] = result["contact_id"]
        meta["ghl_early_contact_status"] = result.get("status")
        conversation.metadata_ = meta
        db.add(conversation)
        db.flush()
    return result


def get_ghl_client(settings: Settings | None = None) -> GHLClient:
    return GHLClient(settings=settings)
