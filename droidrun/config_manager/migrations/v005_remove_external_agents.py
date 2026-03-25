"""Migration v5: Remove legacy external agent configs (mai_ui, autoglm)."""

from typing import Any, Dict

VERSION = 5


def migrate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Remove legacy mai_ui and autoglm entries, reset name if it was one of those."""
    # Remove only the known legacy agent configs, leave user-added ones intact
    external_agents = config.get("external_agents", {})
    if isinstance(external_agents, dict):
        external_agents.pop("mai_ui", None)
        external_agents.pop("autoglm", None)

    # Reset agent.name only if it was a removed agent
    agent = config.get("agent", {})
    if agent.get("name") in ("mai_ui", "autoglm"):
        agent.pop("name", None)

    return config
