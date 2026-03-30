"""IOSDriver — HTTP REST-based device driver for iOS.

Wraps the iOS portal HTTP API (running on the device) to provide device I/O
through the same ``DeviceDriver`` interface used by Android.

Known limitations:
- ``get_apps`` returns a hardcoded list of system bundle identifiers
- ``packageName`` is not tracked (iOS has no API to detect the foreground app)
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
        "get_date",
    }

    supported_buttons = {"home", "back"}

    _BUTTON_IOS_KEYCODES = {
        "home": 1,  # XCUIDeviceButtonHome = 1
    }

    def __init__(
        self,
        url: str,
        bundle_identifiers: Optional[List[str]] = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.bundle_identifiers = bundle_identifiers or []
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False

    # -- lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self.url, timeout=30.0)
        self._connected = True
        logger.info(f"Connected to iOS device at {self.url}")

    async def ensure_connected(self) -> None:
        if not self._connected:
            await self.connect()

    # -- input actions -------------------------------------------------------

    async def tap(self, x: int, y: int) -> None:
        ios_rect = f"{{{{{x},{y}}},{{{1},{1}}}}}"
        resp = await self._client.post(
            "/gestures/tap",
            json={"rect": ios_rect, "count": 1, "longPress": False},
        )
        resp.raise_for_status()

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: float = 1000
    ) -> None:
        resp = await self._client.post(
            "/gestures/swipe",
            json={
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),
                "durationMs": float(duration_ms),
            },
        )
        resp.raise_for_status()

    async def input_text(self, text: str, clear: bool = False) -> bool:
        resp = await self._client.post(
            "/inputs/type", json={"text": text, "clear": clear}
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
        if button_lower == "back":
            resp = await self._client.post("/gestures/back")
            resp.raise_for_status()
            return
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
        """Return unified state from the iOS portal.

        Returns a dict with ``a11y_tree``, ``phone_state``, and
        ``device_context`` keys — matching the format expected by
        ``fetch_state_with_retry()``.
        """
        resp = await self._client.get("/state_full")
        resp.raise_for_status()
        return resp.json()

    async def get_date(self) -> str:
        resp = await self._client.get("/device/date")
        if resp.status_code == 200:
            return resp.json().get("date", "")
        return ""
