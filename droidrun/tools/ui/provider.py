"""StateProvider — orchestrates fetching and parsing device state.

Fetches raw data from a ``DeviceDriver``, applies tree filters/formatters,
and produces a ``UIState`` snapshot.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from droidrun.tools.ui.state import UIState

if TYPE_CHECKING:
    from droidrun.tools.driver.base import DeviceDriver
    from droidrun.tools.filters import TreeFilter
    from droidrun.tools.formatters import TreeFormatter

logger = logging.getLogger("droidrun")


class StateProvider:
    """Base class — subclass to support different platforms."""

    async def get_state(self, driver: "DeviceDriver") -> UIState:
        raise NotImplementedError


class AndroidStateProvider(StateProvider):
    """Fetches state from an Android device via ``driver.get_ui_tree()``.

    Includes retry logic (3 attempts) matching the original
    ``AdbTools.get_state()`` behaviour.
    """

    def __init__(
        self,
        tree_filter: "TreeFilter",
        tree_formatter: "TreeFormatter",
        use_normalized: bool = False,
    ) -> None:
        self.tree_filter = tree_filter
        self.tree_formatter = tree_formatter
        self.use_normalized = use_normalized

    async def get_state(self, driver: "DeviceDriver") -> UIState:
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Getting state (attempt {attempt + 1}/{max_retries})"
                )

                combined_data = await driver.get_ui_tree()

                if "error" in combined_data:
                    raise Exception(
                        f"Portal returned error: "
                        f"{combined_data.get('message', 'Unknown error')}"
                    )

                required_keys = ["a11y_tree", "phone_state", "device_context"]
                missing = [
                    k for k in required_keys if k not in combined_data
                ]
                if missing:
                    raise Exception(
                        f"Missing data in state: {', '.join(missing)}"
                    )

                device_context = combined_data["device_context"]
                screen_bounds = device_context.get("screen_bounds", {})
                screen_width = screen_bounds.get("width")
                screen_height = screen_bounds.get("height")

                filtered = self.tree_filter.filter(
                    combined_data["a11y_tree"], device_context
                )

                self.tree_formatter.screen_width = screen_width
                self.tree_formatter.screen_height = screen_height
                self.tree_formatter.use_normalized = self.use_normalized

                formatted_text, focused_text, elements, phone_state = (
                    self.tree_formatter.format(
                        filtered, combined_data["phone_state"]
                    )
                )

                return UIState(
                    elements=elements,
                    formatted_text=formatted_text,
                    focused_text=focused_text,
                    phone_state=phone_state,
                    screen_width=screen_width,
                    screen_height=screen_height,
                    use_normalized=self.use_normalized,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"get_state attempt {attempt + 1} failed: {last_error}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    error_msg = (
                        f"Failed to get state after {max_retries} "
                        f"attempts: {last_error}"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from last_error
