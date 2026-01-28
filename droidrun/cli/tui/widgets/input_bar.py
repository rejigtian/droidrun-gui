"""Custom input widget with command history and slash detection."""

from __future__ import annotations

from textual.widgets import Input
from textual.message import Message
from textual import events


class InputBar(Input):
    """Input bar with command history and slash command detection."""

    class Submitted(Message):
        """Posted when user presses Enter."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    class SlashChanged(Message):
        """Posted when slash query changes (for dropdown filtering)."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class SlashExited(Message):
        """Posted when input no longer starts with /."""
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._was_slash: bool = False

    @property
    def history(self) -> list[str]:
        return list(self._history)

    def _on_key(self, event: events.Key) -> None:
        if event.key == "up":
            event.prevent_default()
            event.stop()
            self._navigate_history(-1)
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self._navigate_history(1)
        elif event.key == "enter":
            event.prevent_default()
            event.stop()
            self._submit()

    def _navigate_history(self, direction: int) -> None:
        """Navigate command history. -1 = older, 1 = newer."""
        if not self._history:
            return

        if direction == -1:
            # Going back in history
            if self._history_index == -1:
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            else:
                return
        else:
            # Going forward in history
            if self._history_index == -1:
                return
            elif self._history_index < len(self._history) - 1:
                self._history_index += 1
            else:
                # Past the end, clear
                self._history_index = -1
                self.value = ""
                return

        self.value = self._history[self._history_index]
        self.cursor_position = len(self.value)

    def _submit(self) -> None:
        """Handle Enter key."""
        text = self.value.strip()
        if not text:
            return

        # Add to history (avoid consecutive duplicates)
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._history_index = -1

        self.post_message(self.Submitted(text))
        self.value = ""

    def watch_value(self, value: str) -> None:
        """React to value changes for slash detection."""
        is_slash = value.startswith("/")

        if is_slash:
            # Extract query after /
            query = value[1:]
            self.post_message(self.SlashChanged(query))
            self._was_slash = True
        elif self._was_slash:
            self.post_message(self.SlashExited())
            self._was_slash = False

    def clear_input(self) -> None:
        """Clear the input text."""
        self.value = ""
        self._history_index = -1
