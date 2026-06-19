from __future__ import annotations

import random

AGENT_PERSONAS = ["Robert", "Olivia", "Al"]


def assign_agent_name() -> str:
    return random.choice(AGENT_PERSONAS)


def get_agent_name(metadata: dict | None) -> str:
    if metadata and metadata.get("agent_name") in AGENT_PERSONAS:
        return str(metadata["agent_name"])
    return assign_agent_name()
