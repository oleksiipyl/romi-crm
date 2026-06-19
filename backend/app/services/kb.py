from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


class KnowledgeBase:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    @property
    def company(self) -> dict[str, Any]:
        return self.data.get("company", {})

    @property
    def hours(self) -> dict[str, Any]:
        return self.data.get("hours", {})

    @property
    def service_area(self) -> dict[str, Any]:
        return self.data.get("service_area", {})

    @property
    def services(self) -> list[dict[str, Any]]:
        return self.data.get("services", [])

    @property
    def faq(self) -> list[dict[str, Any]]:
        return self.data.get("faq", [])

    def get_service(self, service_id: str) -> dict[str, Any] | None:
        for svc in self.services:
            if svc["service_id"] == service_id:
                return svc
        return None

    def find_service_by_keywords(self, text: str) -> dict[str, Any] | None:
        text_lower = text.lower()
        best: dict[str, Any] | None = None
        best_score = 0
        for svc in self.services:
            score = sum(1 for kw in svc.get("keywords", []) if kw in text_lower)
            if svc["name"].lower() in text_lower:
                score += 3
            if score > best_score:
                best_score = score
                best = svc
        return best

    def is_in_service_zone(self, zip_code: str) -> bool:
        if not zip_code or len(zip_code) < 5:
            return True
        prefix = zip_code[:3]
        la_prefixes = {str(i) for i in range(900, 919)}
        return prefix in la_prefixes

    def build_context_block(self) -> str:
        company = self.company
        lines = [
            f"Company: {company.get('name')} — {company.get('tagline', '')}",
            f"Address: {company.get('address')}",
            f"Phones: general {company.get('phones', {}).get('general')}, "
            f"emergency {company.get('phones', {}).get('main_emergency')}",
            f"Hours: {self.hours.get('weekday')}; {self.hours.get('saturday')}; "
            f"Emergency: {self.hours.get('emergency')}",
            f"Service area: {self.service_area.get('radius_miles')} miles from "
            f"{self.service_area.get('center')}",
            f"Yelp: {company.get('yelp_rating')} stars, {company.get('yelp_reviews')} reviews",
        ]
        return "\n".join(lines)

    def services_summary(self, limit: int = 15) -> str:
        lines = []
        for svc in self.services[:limit]:
            lines.append(
                f"- {svc['service_id']}: {svc['name']} "
                f"(${svc['base_price_min']}-${svc['base_price_max']})"
            )
        if len(self.services) > limit:
            lines.append(f"... and {len(self.services) - limit} more services in catalog")
        return "\n".join(lines)

    def abandon_presentation(self, name: str = "there") -> str:
        block = self.data.get("abandon_presentation", {})
        template = block.get("message", "")
        return template.format(name=name) if template else ""


def load_kb_from_path(path: Path) -> KnowledgeBase:
    with path.open(encoding="utf-8") as f:
        return KnowledgeBase(json.load(f))


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    settings = get_settings()
    return load_kb_from_path(settings.kb_file_path)
