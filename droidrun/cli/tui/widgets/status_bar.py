"""Status bar widget showing device, mode, and step count."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.app import RenderResult
from rich.text import Text


class StatusBar(Widget):
    """Persistent status bar at the bottom of the TUI."""

    device_name: reactive[str] = reactive("no device")
    device_connected: reactive[bool] = reactive(False)
    mode: reactive[str] = reactive("fast")
    current_step: reactive[int] = reactive(0)
    max_steps: reactive[int] = reactive(15)
    is_running: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: #22223a;
        padding: 0 1;
    }
    """

    def render(self) -> RenderResult:
        bar = Text()

        # Device indicator
        if self.device_connected:
            bar.append(" \u25cf ", style="bold #a6da95")
            bar.append(self.device_name, style="#a6da95")
        else:
            bar.append(" \u25cf ", style="bold #ed8796")
            bar.append(self.device_name, style="#ed8796")

        bar.append("  \u2502  ", style="#47475e")

        # Mode
        bar.append(self.mode, style="bold #CAD3F6")

        # Step count (only when running)
        if self.is_running and self.max_steps > 0:
            bar.append("  \u2502  ", style="#47475e")
            bar.append(f"step {self.current_step}/{self.max_steps}", style="#f5a97f")

        return bar
