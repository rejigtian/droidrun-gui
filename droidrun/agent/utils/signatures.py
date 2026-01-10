"""Action signatures and filtering utilities."""

import logging
from typing import Any, Dict, List

from droidrun.agent.utils.actions import (
    click,
    click_at,
    click_area,
    complete,
    long_press,
    long_press_at,
    open_app,
    remember,
    swipe,
    system_button,
    type,
    type_secret,
    wait,
)


ATOMIC_ACTION_SIGNATURES = {
    "click": {
        "arguments": ["index"],
        "description": 'Click the point on the screen with specified index. Usage Example: {"action": "click", "index": element_index}',
        "function": click,
    },
    "long_press": {
        "arguments": ["index"],
        "description": 'Long press on the position with specified index. Usage Example: {"action": "long_press", "index": element_index}',
        "function": long_press,
    },
    "click_at": {
        "arguments": ["x", "y"],
        "description": 'Click at screen position (x, y). Use element bounds as reference to determine where to click. Usage: {"action": "click_at", "x": 500, "y": 300}',
        "function": click_at,
    },
    "click_area": {
        "arguments": ["x1", "y1", "x2", "y2"],
        "description": 'Click center of area (x1, y1, x2, y2). Useful when you want to click a specific region. Usage: {"action": "click_area", "x1": 100, "y1": 200, "x2": 300, "y2": 400}',
        "function": click_area,
    },
    "long_press_at": {
        "arguments": ["x", "y"],
        "description": 'Long press at screen position (x, y). Use element bounds as reference. Usage: {"action": "long_press_at", "x": 500, "y": 300}',
        "function": long_press_at,
    },
    "type": {
        "arguments": ["text", "index", "clear=False"],
        "description": 'Type text into an input box or text field. Specify the element with index to focus the input field before typing. By default, text is APPENDED to existing content. Set clear=True to clear the field first (recommended for URL bars, search fields, or when replacing text). Usage Example: {"action": "type", "text": "example.com", "index": element_index, "clear": true}',
        "function": type,
    },
    "system_button": {
        "arguments": ["button"],
        "description": 'Press a system button, including back, home, and enter. Usage example: {"action": "system_button", "button": "Home"}',
        "function": system_button,
    },
    "swipe": {
        "arguments": ["coordinate", "coordinate2", "duration=1.0"],
        "description": 'Scroll from the position with coordinate to the position with coordinate2. Duration is in seconds (default: 1.0). Usage Example: {"action": "swipe", "coordinate": [x1, y1], "coordinate2": [x2, y2], "duration": 1.5}',
        "function": swipe,
    },
    "wait": {
        "arguments": ["duration"],
        "description": 'Wait for a specified duration in seconds. Useful for waiting for animations, page loads, or other time-based operations. Usage Example: {"action": "wait", "duration": 2.0}',
        "function": wait,
    },
}


def filter_atomic_actions(disabled_tools: List[str]) -> Dict[str, Any]:
    """Filter ATOMIC_ACTION_SIGNATURES by removing disabled tools."""
    if not disabled_tools:
        return ATOMIC_ACTION_SIGNATURES.copy()
    return {k: v for k, v in ATOMIC_ACTION_SIGNATURES.items() if k not in disabled_tools}


def filter_custom_tools(
    custom_tools: Dict[str, Any],
    disabled_tools: List[str],
) -> Dict[str, Any]:
    """Filter custom tools dict by removing disabled tools."""
    if not custom_tools:
        return {}
    if not disabled_tools:
        return custom_tools.copy()
    return {k: v for k, v in custom_tools.items() if k not in disabled_tools}


def get_atomic_tool_descriptions() -> str:
    """Get formatted tool descriptions for CodeAct system prompt."""
    descriptions = []
    for action_name, signature in ATOMIC_ACTION_SIGNATURES.items():
        args = ", ".join(signature["arguments"])
        desc = signature["description"]
        descriptions.append(f"- {action_name}({args}): {desc}")
    return "\n".join(descriptions)


def build_custom_tool_descriptions(custom_tools: dict) -> str:
    """Build formatted tool descriptions from custom_tools dict."""
    if not custom_tools:
        return ""
    descriptions = []
    for action_name, signature in custom_tools.items():
        args = ", ".join(signature.get("arguments", []))
        desc = signature.get("description", f"Custom action: {action_name}")
        descriptions.append(f"- {action_name}({args}): {desc}")
    return "\n".join(descriptions)


async def build_credential_tools(credential_manager) -> dict:
    """Build credential-related custom tools if credential manager is available."""
    logger = logging.getLogger("droidrun")

    if credential_manager is None:
        return {}

    available_secrets = await credential_manager.get_keys()
    if not available_secrets:
        logger.debug("No enabled secrets found, credential tools disabled")
        return {}

    logger.debug(f"Building credential tools with {len(available_secrets)} secrets")

    return {
        "type_secret": {
            "arguments": ["secret_id", "index"],
            "description": 'Type a secret credential from the credential store into an input field. The agent never sees the actual secret value, only the secret_id. Usage: {"action": "type_secret", "secret_id": "MY_PASSWORD", "index": 5}',
            "function": type_secret,
        },
    }


async def build_custom_tools(credential_manager=None) -> dict:
    """Build all custom tools (credentials + utility tools)."""
    logger = logging.getLogger("droidrun")
    custom_tools = {}

    credential_tools = await build_credential_tools(credential_manager)
    custom_tools.update(credential_tools)

    if credential_tools:
        logger.debug(f"Built {len(credential_tools)} credential tools: {list(credential_tools.keys())}")

    custom_tools["open_app"] = {
        "arguments": ["text"],
        "description": 'Open an app by name or description. Usage: {"action": "open_app", "text": "Gmail"}',
        "function": open_app,
    }

    return custom_tools
