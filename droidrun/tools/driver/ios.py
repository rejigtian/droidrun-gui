"""IOSDriver — HTTP REST-based device driver for iOS.

Wraps the iOS portal HTTP API (running on the device) to provide device I/O
through the same ``DeviceDriver`` interface used by Android.

Known limitations (pre-existing, documented as TODOs):
- ``clear`` parameter in ``input_text`` is ignored
- ``press_button`` only supports HOME; BACK and ENTER have no iOS equivalent
- ``get_date`` not available (no iOS portal endpoint)
- ``drag`` not implemented
- ``get_apps`` returns bundle identifiers, not real app metadata
- Screen dimensions inferred from element bounds (no portal endpoint)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from droidrun.tools.driver.base import DeviceDriver

logger = logging.getLogger("droidrun")

SYSTEM_BUNDLE_IDENTIFIERS = [
    "ai.droidrun.droidrun-ios-portal",
    "com.apple.Bridge",
    "com.apple.DocumentsApp",
    "com.apple.Fitness",
    "com.apple.Health",
    "com.apple.Maps",
    "com.apple.MobileAddressBook",
    "com.apple.MobileSMS",
    "com.apple.Passbook",
    "com.apple.Passwords",
    "com.apple.Preferences",
    "com.apple.PreviewShell",
    "com.apple.mobilecal",
    "com.apple.mobilesafari",
    "com.apple.mobileslideshow",
    "com.apple.news",
    "com.apple.reminders",
    "com.apple.shortcuts",
    "com.apple.webapp",
]


class IOSDriver(DeviceDriver):
    """iOS device driver communicating via HTTP REST to the iOS portal app."""

    platform = "iOS"

    supported = {
        "tap",
        "swipe",
        "input_text",
        "press_button",
        "start_app",
        "screenshot",
        "get_ui_tree",
        "list_packages",
        "get_apps",
    }

    supported_buttons = {"home"}

    _BUTTON_IOS_KEYCODES = {
        "home": 0,
    }

    def __init__(
        self,
        url: str,
        bundle_identifiers: Optional[List[str]] = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.bundle_identifiers = bundle_identifiers or []
        self._client: Optional[httpx.AsyncClient] = None
        self._last_tapped_rect: Optional[str] = None
        self._connected = False

    # -- lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self.url, timeout=30.0)
        # TODO: verify URL is reachable (ping /vision/state or similar)
        self._connected = True
        logger.info(f"Connected to iOS device at {self.url}")

    async def ensure_connected(self) -> None:
        if not self._connected:
            await self.connect()

    # -- input actions -------------------------------------------------------

    async def tap(self, x: int, y: int) -> None:
        ios_rect = f"{{{{{x},{y}}},{{{1},{1}}}}}"
        # Store for input_text (iOS API requires a rect for typing)
        # TODO: stores center point as 1x1 rect, not full element bounds
        self._last_tapped_rect = f"{x},{y},1,1"
        resp = await self._client.post(
            "/gestures/tap",
            json={"rect": ios_rect, "count": 1, "longPress": False},
        )
        resp.raise_for_status()

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: float = 1000
    ) -> None:
        # iOS API is direction-based, not coordinate-based
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) > abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"
        resp = await self._client.post(
            "/gestures/swipe",
            json={"x": float(x1), "y": float(y1), "dir": direction},
        )
        resp.raise_for_status()

    async def input_text(self, text: str, clear: bool = False) -> bool:
        # TODO: clear not supported on iOS portal
        rect = self._last_tapped_rect or "0,0,100,100"
        resp = await self._client.post(
            "/inputs/type", json={"rect": rect, "text": text}
        )
        return resp.status_code == 200

    async def press_button(self, button: str) -> None:
        await self.ensure_connected()
        button_lower = button.lower()
        if button_lower not in self.supported_buttons:
            raise ValueError(
                f"Button '{button}' not supported on iOS. "
                f"Supported: {', '.join(sorted(self.supported_buttons))}"
            )
        keycode = self._BUTTON_IOS_KEYCODES[button_lower]
        resp = await self._client.post("/inputs/key", json={"key": keycode})
        resp.raise_for_status()

    # -- app management ------------------------------------------------------

    async def start_app(self, package: str, activity: Optional[str] = None) -> str:
        resp = await self._client.post(
            "/inputs/launch", json={"bundleIdentifier": package}
        )
        if resp.status_code == 200:
            return f"Launched {package}"
        return f"Failed to launch {package}: HTTP {resp.status_code}"

    async def get_apps(self, include_system: bool = True) -> List[Dict[str, str]]:
        # TODO: iOS portal has no app listing endpoint.
        # Returns bundle identifiers as both package and label.
        all_ids: set[str] = set(self.bundle_identifiers)
        if include_system:
            all_ids.update(SYSTEM_BUNDLE_IDENTIFIERS)
        return [{"package": bid, "label": bid} for bid in sorted(all_ids)]

    async def list_packages(self, include_system: bool = False) -> List[str]:
        apps = await self.get_apps(include_system)
        return [a["package"] for a in apps]

    # -- state / observation -------------------------------------------------

    async def screenshot(self, hide_overlay: bool = True) -> bytes:
        resp = await self._client.get("/vision/screenshot")
        resp.raise_for_status()
        return resp.content

    async def get_ui_tree(self) -> Dict[str, Any]:
        """Return raw iOS accessibility data and phone state.

        Returns a dict with:
        - ``a11y_raw``: the raw accessibility tree text from the portal
        - ``phone_state``: dict with ``current_activity`` and ``keyboard_shown``
        """
        a11y_resp = await self._client.get("/vision/a11y")
        a11y_resp.raise_for_status()
        a11y_data = a11y_resp.json()

        state_resp = await self._client.get("/vision/state")
        if state_resp.status_code == 200:
            state_data = state_resp.json()
            phone_state = {
                "currentApp": state_data.get("activity", "Unknown"),
                "keyboardVisible": state_data.get("keyboardShown", False),
            }
        else:
            phone_state = {
                "currentApp": "Unknown",
                "keyboardVisible": False,
            }

        return {
            "a11y_raw": a11y_data["accessibilityTree"],
            "phone_state": phone_state,
        }

    async def get_date(self) -> str:
        # TODO: not available on iOS portal
        return ""
