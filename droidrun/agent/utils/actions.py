"""Action functions for device interaction."""

import asyncio
import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from droidrun.tools import Tools

from droidrun.agent.common.events import WaitEvent
from droidrun.agent.oneflows.app_starter_workflow import AppStarter


async def click(index: int, *, tools: "Tools" = None, **kwargs) -> str:
    """Click the element with the given index."""
    if tools is None:
        raise ValueError("tools parameter is required")
    return await tools.tap_by_index(index)


async def long_press(index: int, *, tools: "Tools" = None, **kwargs) -> bool:
    """Long press the element with the given index."""
    if tools is None:
        raise ValueError("tools parameter is required")
    x, y = tools._extract_element_coordinates_by_index(index)
    return await tools.swipe(x, y, x, y, 1000)


async def long_press_at(x: int, y: int, *, tools: "Tools" = None, **kwargs) -> bool:
    """Long press at screen coordinates."""
    if tools is None:
        raise ValueError("tools parameter is required")
    abs_x, abs_y = tools.convert_point(x, y)
    return await tools.swipe(abs_x, abs_y, abs_x, abs_y, 1000)


async def click_at(x: int, y: int, *, tools: "Tools" = None, **kwargs) -> str:
    """Click at screen coordinates."""
    if tools is None:
        raise ValueError("tools parameter is required")
    abs_x, abs_y = tools.convert_point(x, y)
    return await tools.tap_by_coordinates(abs_x, abs_y)


async def click_area(
    x1: int, y1: int, x2: int, y2: int, *, tools: "Tools" = None, **kwargs
) -> str:
    """Click center of area."""
    if tools is None:
        raise ValueError("tools parameter is required")
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    abs_x, abs_y = tools.convert_point(cx, cy)
    return await tools.tap_by_coordinates(abs_x, abs_y)


async def type(
    text: str, index: int, clear: bool = False, *, tools: "Tools" = None, **kwargs
) -> str:
    """Type text into the element with the given index."""
    if tools is None:
        raise ValueError("tools parameter is required")
    return await tools.input_text(text, index, clear=clear)


async def system_button(button: str, *, tools: "Tools" = None, **kwargs) -> str:
    """Press a system button (back, home, or enter)."""
    if tools is None:
        raise ValueError("tools parameter is required")

    button_map = {"back": 4, "home": 3, "enter": 66}
    button_lower = button.lower()

    if button_lower not in button_map:
        return f"Error: Unknown system button '{button}'. Valid options: back, home, enter"

    keycode = button_map[button_lower]
    return await tools.press_key(keycode)


async def swipe(
    coordinate: List[int],
    coordinate2: List[int],
    duration: float = 1.0,
    *,
    tools: "Tools" = None,
    **kwargs,
) -> bool:
    """Swipe from one coordinate to another."""
    if tools is None:
        raise ValueError("tools parameter is required")

    if not isinstance(coordinate, list) or len(coordinate) != 2:
        raise ValueError(f"coordinate must be a list of 2 integers, got: {coordinate}")
    if not isinstance(coordinate2, list) or len(coordinate2) != 2:
        raise ValueError(f"coordinate2 must be a list of 2 integers, got: {coordinate2}")

    start_x, start_y = tools.convert_point(*coordinate)
    end_x, end_y = tools.convert_point(*coordinate2)

    duration_ms = int(duration * 1000)
    return await tools.swipe(start_x, start_y, end_x, end_y, duration_ms=duration_ms)


async def open_app(text: str, *, tools: "Tools" = None, **kwargs) -> str:
    """Open an app by its name."""
    if tools is None:
        raise ValueError("tools parameter is required")

    if tools.app_opener_llm is None:
        raise RuntimeError(
            "app_opener_llm not configured. Provide app_opener_llm when initializing Tools."
        )

    workflow = AppStarter(
        tools=tools,
        llm=tools.app_opener_llm,
        timeout=60,
        stream=tools.streaming,
        verbose=False,
    )

    result = await workflow.run(app_description=text)
    await asyncio.sleep(1)
    return result


async def wait(duration: float = 1.0, *, tools: "Tools" = None, **kwargs) -> str:
    """Wait for a specified duration in seconds."""
    if tools is not None and hasattr(tools, "_ctx") and tools._ctx is not None:
        wait_event = WaitEvent(
            action_type="wait",
            description=f"Wait for {duration} seconds",
            duration=duration,
        )
        tools._ctx.write_event_to_stream(wait_event)

    await asyncio.sleep(duration)
    return f"Waited for {duration} seconds"


def remember(information: str, *, tools: "Tools" = None, **kwargs) -> str:
    """Remember important information for later use."""
    if tools is None:
        raise ValueError("tools parameter is required")
    return tools.remember(information)


async def complete(
    success: bool, reason: str = "", *, tools: "Tools" = None, **kwargs
) -> None:
    """Mark the task as complete."""
    if tools is None:
        raise ValueError("tools parameter is required")
    await tools.complete(success, reason)


async def type_secret(
    secret_id: str, index: int, *, tools: "Tools" = None, **kwargs
) -> str:
    """Type a secret credential into an input field without exposing the value."""
    logger = logging.getLogger("droidrun")

    if tools is None:
        raise ValueError("tools parameter is required")

    if not hasattr(tools, "credential_manager") or tools.credential_manager is None:
        return "Error: Credential manager not initialized. Enable credentials in config.yaml"

    try:
        secret_value = await tools.credential_manager.resolve_key(secret_id)
        await tools.input_text(secret_value, index)
        return f"Successfully typed secret '{secret_id}' into element {index}"
    except Exception as e:
        logger.error(f"Failed to type secret '{secret_id}': {e}")
        available = (
            await tools.credential_manager.get_keys()
            if tools.credential_manager
            else []
        )
        return f"Error: Secret '{secret_id}' not found. Available: {available}"
