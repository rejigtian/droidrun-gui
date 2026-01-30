"""Selectable log view built on TextArea."""

from __future__ import annotations

from textual import events
from textual.widgets import TextArea


class LogView(TextArea):
    """Read-only log view with text selection and copy support.

    Replaces RichLog which has no selection support. Trades Rich-styled
    colored output for mouse/keyboard text selection and ctrl+c copy.
    Auto-copies to clipboard when a mouse selection finishes.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            read_only=True,
            show_line_numbers=False,
            show_cursor=False,
            soft_wrap=True,
            **kwargs,
        )

    async def _on_mouse_up(self, event: events.MouseUp) -> None:
        await super()._on_mouse_up(event)
        if not self.selection.is_empty:
            text = self.selected_text
            if text:
                self.app.copy_to_clipboard(text)
                self.app.notify("Copied", timeout=1.5)

    def append(self, line: str) -> None:
        """Append a line of text and auto-scroll to bottom."""
        end = self.document.end
        prefix = "\n" if end != (0, 0) else ""
        self.insert(prefix + line, location=end, maintain_selection_offset=True)
        self.scroll_end(animate=False)

    def clear_log(self) -> None:
        """Clear all log content."""
        self.load_text("")
