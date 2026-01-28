"""Dropdown widget for slash command selection."""

from __future__ import annotations

from textual.widget import Widget
from textual.message import Message
from textual.app import RenderResult
from textual.reactive import reactive
from rich.text import Text

from droidrun.cli.tui.commands import Command


class CommandDropdown(Widget):
    """Dropdown that appears below input when typing slash commands."""

    class Selected(Message):
        """Posted when a command is selected."""

        def __init__(self, command_name: str) -> None:
            super().__init__()
            self.command_name = command_name

    highlighted: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    CommandDropdown {
        height: auto;
        max-height: 10;
        background: #22223a;
        border: solid #47475e;
        margin: 0 1;
        padding: 0;
    }
    CommandDropdown.hidden {
        display: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._commands: list[Command] = []

    def update_commands(self, commands: list[Command]) -> None:
        """Update the displayed commands and reset highlight."""
        self._commands = commands
        self.highlighted = 0
        self.refresh()

    def move_highlight(self, direction: int) -> None:
        """Move highlight up (-1) or down (1)."""
        if not self._commands:
            return
        new_idx = self.highlighted + direction
        self.highlighted = max(0, min(new_idx, len(self._commands) - 1))

    def select_highlighted(self) -> None:
        """Select the currently highlighted command."""
        if self._commands and 0 <= self.highlighted < len(self._commands):
            cmd = self._commands[self.highlighted]
            self.post_message(self.Selected(cmd.name))

    @property
    def has_commands(self) -> bool:
        return bool(self._commands)

    def render(self) -> RenderResult:
        if not self._commands:
            line = Text("  No matching commands", style="#47475e italic")
            return line

        output = Text()
        for i, cmd in enumerate(self._commands):
            if i > 0:
                output.append("\n")

            is_highlighted = i == self.highlighted

            if is_highlighted:
                output.append("  /", style="bold #CAD3F6 on #2e2e4a")
                output.append(f"{cmd.name:<14}", style="bold #CAD3F6 on #2e2e4a")
                output.append(cmd.description, style="#CAD3F6 on #2e2e4a")
                # Pad to fill width
                remaining = max(0, 60 - len(cmd.name) - len(cmd.description) - 3)
                output.append(" " * remaining, style="on #2e2e4a")
            else:
                output.append("  /", style="#838BBC")
                output.append(f"{cmd.name:<14}", style="bold #838BBC")
                output.append(cmd.description, style="#47475e")

        return output
