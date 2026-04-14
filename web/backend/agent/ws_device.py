"""
WebSocketDevice — subclasses droidrun's DeviceDriver to bridge tool calls
to a Portal Android app connected via reverse WebSocket (JSON-RPC).
"""

import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from droidrun.tools.driver.base import DeviceDriver

from ws.portal_ws import DeviceConnection, send_rpc

logger = logging.getLogger(__name__)

# Android key codes
_KEY_CODES = {
    "back": 4,
    "home": 3,
    "recent": 187,
    "enter": 66,
    "del": 67,
    "tab": 61,
    "space": 62,
}


class WebSocketDevice(DeviceDriver):
    """
    DeviceDriver that relays every tool call to a Portal app via JSON-RPC over
    the persistent WebSocket connection managed by portal_ws.py.
    """

    platform = "Android"
    supported = {
        "tap",
        "swipe",
        "input_text",
        "press_button",
        "drag",
        "screenshot",
        "get_ui_tree",
        "get_date",
        "start_app",
        "get_apps",
        "list_packages",
    }
    supported_buttons = set(_KEY_CODES.keys())

    def __init__(self, connection: DeviceConnection):
        self.connection = connection

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        # Connection is already established by portal_ws.py
        pass

    async def ensure_connected(self) -> None:
        if not self.connection.is_connected:
            raise RuntimeError(
                f"Device {self.connection.device_id} is not connected"
            )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    async def _rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Any:
        await self.ensure_connected()
        return await send_rpc(self.connection, method, params, timeout=timeout)

    # ------------------------------------------------------------------
    # Gesture / Input
    # ------------------------------------------------------------------

    async def tap(self, x: int, y: int) -> None:
        await self._rpc("tap", {"x": x, "y": y})

    async def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 1000,
    ) -> None:
        await self._rpc(
            "swipe",
            {
                "startX": x1,
                "startY": y1,
                "endX": x2,
                "endY": y2,
                "duration": duration_ms,
            },
        )

    async def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: int = 1000,
    ) -> None:
        # Portal doesn't have a dedicated drag; simulate with a slow swipe
        await self.swipe(x1, y1, x2, y2, duration_ms=duration)

    async def input_text(
        self,
        text: str,
        clear: bool = False,
        stealth: bool = False,
        wpm: int = 0,
    ) -> bool:
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        await self._rpc("keyboard/input", {"base64_text": encoded, "clear": clear})
        return True

    async def press_button(self, button: str) -> None:
        key_code = _KEY_CODES.get(button)
        if key_code is None:
            raise ValueError(f"Unsupported button: {button!r}")
        await self._rpc("keyboard/key", {"key_code": key_code})

    # ------------------------------------------------------------------
    # Screen / State
    # ------------------------------------------------------------------

    async def screenshot(self, hide_overlay: bool = True) -> bytes:
        result = await self._rpc(
            "screenshot", {"hideOverlay": hide_overlay}, timeout=15.0
        )
        # Portal returns base64-encoded PNG (string or {"data": "..."})
        if isinstance(result, str):
            b64 = result
        elif isinstance(result, dict):
            b64 = result.get("data") or result.get("image") or result.get("screenshot", "")
        else:
            b64 = str(result)
        return base64.b64decode(b64)

    async def get_ui_tree(self) -> Dict[str, Any]:
        """
        Returns {"a11y_tree": ..., "phone_state": ..., "device_context": {...}}
        Portal RPC method is "state" with params {filter: true}.
        """
        result = await self._rpc("state", {"filter": True}, timeout=30.0)
        if result is None:
            result = {}
        # Ensure device_context exists (older builds may omit it)
        if "device_context" not in result:
            result["device_context"] = {}
        return result

    async def get_date(self) -> str:
        try:
            result = await self._rpc("time", {})
            if isinstance(result, (int, float)):
                ts = result / 1000
            elif isinstance(result, dict):
                ts = result.get("timestamp", 0) / 1000
            else:
                ts = 0
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # App management
    # ------------------------------------------------------------------

    async def start_app(self, package: str, activity: Optional[str] = None) -> str:
        await self._rpc(
            "app",
            {"package": package, "activity": activity or "", "stopBeforeLaunch": False},
        )
        return f"Started {package}"

    async def install_app(self, path: str, **kwargs) -> str:
        # Install from URL — Portal supports install method with url param
        await self._rpc(
            "install",
            {"url": path, "hideOverlay": True},
            timeout=120.0,
        )
        return f"Installed from {path}"

    async def get_apps(self, include_system: bool = False) -> List[Dict[str, str]]:
        result = await self._rpc("packages", {})
        apps: list = result if isinstance(result, list) else result.get("packages", [])
        if not include_system:
            apps = [a for a in apps if not a.get("isSystemApp", False)]
        return [
            {"package": a.get("packageName", ""), "label": a.get("label", "")}
            for a in apps
        ]

    async def list_packages(self, include_system: bool = False) -> List[str]:
        apps = await self.get_apps(include_system=include_system)
        return [a["package"] for a in apps]
