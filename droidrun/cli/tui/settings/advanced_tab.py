"""Advanced tab — TCP, save trajectory, tracing."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Rule, Select, Static, Switch

from droidrun.cli.tui.settings.data import SettingsData

TRACING_PROVIDERS = [
    ("Phoenix", "phoenix"),
    ("Langfuse", "langfuse"),
]


class AdvancedTab(Vertical):
    """Content for the Advanced tab pane."""

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Static("Connection", classes="section-title")

        with Horizontal(classes="switch-row"):
            yield Label("Use TCP", classes="switch-label")
            yield Switch(value=self.settings.use_tcp, id="use-tcp")

        yield Rule()
        yield Static("Logging", classes="section-title")

        with Horizontal(classes="switch-row"):
            yield Label("Trajectory", classes="switch-label")
            yield Switch(value=self.settings.save_trajectory, id="save-trajectory")

        yield Rule()
        yield Static("Tracing", classes="section-title")

        with Horizontal(classes="switch-row"):
            yield Label("Enabled", classes="switch-label")
            yield Switch(value=self.settings.tracing_enabled, id="tracing-enabled")

        with Horizontal(classes="field-row"):
            yield Label("Provider", classes="field-label")
            yield Select(
                TRACING_PROVIDERS,
                value=self.settings.tracing_provider,
                allow_blank=False,
                id="tracing-provider",
                classes="field-select",
            )

    def collect(self) -> dict:
        """Collect current advanced settings."""
        return {
            "use_tcp": self.query_one("#use-tcp", Switch).value,
            "save_trajectory": self.query_one("#save-trajectory", Switch).value,
            "tracing_enabled": self.query_one("#tracing-enabled", Switch).value,
            "tracing_provider": self.query_one("#tracing-provider", Select).value,
        }
