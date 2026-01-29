"""Status bar widget."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.app import RenderResult
from rich.text import Text


class StatusBar(Widget):
    can_focus = False

    device_serial: reactive[str] = reactive("")
    device_name: reactive[str] = reactive("no model")
    mode: reactive[str] = reactive("fast")
    current_step: reactive[int] = reactive(0)
    max_steps: reactive[int] = reactive(15)
    is_running: reactive[bool] = reactive(False)
    hint: reactive[str] = reactive("")

    def render(self) -> RenderResult:
        bar = Text()

        # Device serial
        if self.device_serial:
            bar.append("\u25cf ", style="#a6da95")
            bar.append(self.device_serial, style="#a6da95")
        else:
            bar.append("\u25cf ", style="#ed8796")
            bar.append("no device", style="#ed8796")

        bar.append("  \u2502  ", style="#2e2e4a")

        # Model name
        bar.append(self.device_name, style="#838BBC")

        bar.append("  \u2502  ", style="#2e2e4a")

        # Mode
        bar.append(self.mode, style="#CAD3F6")

        # Steps
        if self.is_running and self.max_steps > 0:
            bar.append("  \u2502  ", style="#2e2e4a")
            bar.append(f"{self.current_step}/{self.max_steps}", style="#f5a97f")

        # Right-aligned hint
        if self.hint:
            try:
                width = self.size.width
                used = bar.cell_len
                gap = max(1, width - used - len(self.hint) - 2)
                bar.append(" " * gap)
                bar.append(self.hint, style="#47475e")
            except Exception:
                pass

        return bar
