"""Reusable section container for settings tabs."""

from __future__ import annotations

from textual.containers import VerticalGroup


class Section(VerticalGroup):
    """A visually grouped section with a border title."""

    def __init__(
        self,
        title: str,
        hint: str = "",
        *children,
        **kwargs,
    ) -> None:
        super().__init__(*children, **kwargs)
        self.border_title = title
        if hint:
            self.border_subtitle = hint
