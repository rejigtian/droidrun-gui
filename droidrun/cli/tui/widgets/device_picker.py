"""Inline device picker widget — keyboard-driven, shown above input bar."""

from __future__ import annotations

from textual.widget import Widget
from textual.message import Message
from textual.app import RenderResult
from textual.reactive import reactive
from textual import events
from rich.text import Text


class DevicePicker(Widget):
    """Inline picker for devices and setup prompts.

    Modes:
        pick   — arrow keys navigate, enter selects a device
        prompt — enter confirms setup, esc cancels
        status — non-interactive text (e.g. "checking…")
    """

    can_focus = True

    class DeviceSelected(Message):
        def __init__(self, serial: str) -> None:
            super().__init__()
            self.serial = serial

    class SetupConfirmed(Message):
        def __init__(self, serial: str) -> None:
            super().__init__()
            self.serial = serial

    class Cancelled(Message):
        pass

    highlighted: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._devices: list[tuple[str, str]] = []  # (serial, state)
        self._mode: str = "pick"  # pick | prompt | status
        self._status_text: str = ""
        self._prompt_serial: str = ""

    # ── Public API ──

    def set_devices(self, devices: list[tuple[str, str]]) -> None:
        self._devices = devices
        self._mode = "pick"
        self.highlighted = 0
        self.refresh()

    def set_status(self, text: str) -> None:
        self._mode = "status"
        self._status_text = text
        self.refresh()

    def set_prompt(self, serial: str, text: str) -> None:
        self._mode = "prompt"
        self._prompt_serial = serial
        self._status_text = text
        self.refresh()

    @property
    def has_devices(self) -> bool:
        return bool(self._devices)

    # ── Keyboard ──

    def on_key(self, event: events.Key) -> None:
        if self._mode == "pick":
            if event.key == "up":
                event.stop()
                event.prevent_default()
                self.highlighted = max(0, self.highlighted - 1)
            elif event.key == "down":
                event.stop()
                event.prevent_default()
                self.highlighted = min(len(self._devices) - 1, self.highlighted + 1)
            elif event.key == "enter":
                event.stop()
                event.prevent_default()
                if self._devices:
                    serial = self._devices[self.highlighted][0]
                    self.post_message(self.DeviceSelected(serial))
            elif event.key == "escape":
                event.stop()
                event.prevent_default()
                self.post_message(self.Cancelled())

        elif self._mode == "prompt":
            if event.key == "enter":
                event.stop()
                event.prevent_default()
                self.post_message(self.SetupConfirmed(self._prompt_serial))
            elif event.key == "escape":
                event.stop()
                event.prevent_default()
                # Back to pick mode
                self._mode = "pick"
                self.refresh()

        elif self._mode == "status":
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self.post_message(self.Cancelled())

    # ── Render ──

    def render(self) -> RenderResult:
        if self._mode == "status":
            return Text(f"  {self._status_text}", style="#52525b")

        if self._mode == "prompt":
            out = Text()
            out.append(f"  {self._status_text}\n", style="#c084fc")
            out.append("  enter", style="bold #c084fc")
            out.append(" to run setup, ", style="#838BBC")
            out.append("esc", style="bold #c084fc")
            out.append(" to cancel", style="#838BBC")
            return out

        # pick mode
        if not self._devices:
            return Text("  no devices found", style="#52525b")

        try:
            total_width = self.size.width - 4
        except Exception:
            total_width = 60

        out = Text()
        for i, (serial, state) in enumerate(self._devices):
            if i > 0:
                out.append("\n")

            hl = i == self.highlighted
            bg = " on #2e2e4a" if hl else ""
            serial_style = f"bold #CAD3F6{bg}"
            state_style = f"#838BBC{bg}" if not hl else f"#a6da95{bg}"

            label = f"  {serial}  ({state})"
            pad = max(0, total_width - len(label))
            out.append(f"  {serial}", style=serial_style)
            out.append(f"  ({state})", style=state_style)
            if hl:
                out.append(" " * pad, style=bg)

        return out
