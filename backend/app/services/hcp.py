from __future__ import annotations

import logging
import re
from typing import Any, Protocol

import httpx

from app.config import Settings, get_settings
from app.services.ghl import normalize_phone

logger = logging.getLogger(__name__)

HCP_BASE_URL = "https://api.housecallpro.com"


class HTTPClient(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


class HCPClient:
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
        return bool(self.settings.hcp_api_key)

    def _client(self) -> HTTPClient:
        if self._http is None:
            self._http = httpx.Client(timeout=15.0)
        return self._http

    def close(self) -> None:
        if self._owns_client and self._http is not None:
            close = getattr(self._http, "close", None)
            if callable(close):
                close()

    def search_customer_by_phone(self, phone: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        digits = normalize_phone(phone)
        if not digits:
            return None

        try:
            response = self._client().request(
                "GET",
                f"{HCP_BASE_URL}/customers",
                headers={
                    "Authorization": f"Token {self.settings.hcp_api_key}",
                    "Accept": "application/json",
                },
                params={"phone": digits, "page_size": 5},
            )
            if response.status_code >= 400:
                logger.warning("HCP API error: %s", response.status_code)
                return None
            data = response.json()
            customers = data.get("customers") or data.get("data") or []
            for customer in customers:
                customer_phone = normalize_phone(
                    customer.get("phone") or customer.get("mobile_number")
                )
                if customer_phone == digits:
                    return {
                        "customer_id": customer.get("id"),
                        "name": customer.get("name") or customer.get("first_name"),
                        "phone": customer.get("phone"),
                    }
        except Exception:
            logger.exception("HCP customer lookup failed")
        return None


def get_hcp_client(settings: Settings | None = None) -> HCPClient:
    return HCPClient(settings=settings)
