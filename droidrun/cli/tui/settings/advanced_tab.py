"""Advanced tab — TCP, prompt directory, save trajectory, tracing."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Select, Static, Switch

from droidrun.cli.tui.settings.data import SettingsData

TRACING_PROVIDERS = [
    ("Phoenix", "phoenix"),
    ("Langfuse", "langfuse"),
]


class AdvancedTab(Vertical):
    """Content for the Advanced tab pane."""

    DEFAULT_CSS = """
    AdvancedTab {
        padding: 1 2;
    }
    AdvancedTab .section-title {
        color: #CAD3F6;
        text-style: bold;
        margin-bottom: 1;
    }
    AdvancedTab .switch-row {
        height: auto;
        margin-bottom: 1;
    }
    AdvancedTab .switch-label {
        width: 18;
        padding-top: 0;
        color: #838BBC;
    }
    AdvancedTab .field-row {
        height: auto;
        margin-bottom: 1;
    }
    AdvancedTab .field-label {
        width: 18;
        padding-top: 1;
        color: #838BBC;
    }
    AdvancedTab .field-input {
        width: 1fr;
    }
    AdvancedTab .field-select {
        width: 1fr;
    }
    AdvancedTab .separator {
        color: #2e2e4a;
        margin: 1 0;
    }
    """

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        # Connection
        yield Static("Connection", classes="section-title")

        with Horizontal(classes="switch-row"):
            yield Label("Use TCP", classes="switch-label")
            yield Switch(value=self.settings.use_tcp, id="use-tcp")

        yield Static("─" * 50, classes="separator")

        # Prompts
        yield Static("Prompts", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Prompt Directory", classes="field-label")
            yield Input(
                value=self.settings.prompt_directory,
                placeholder="config/prompts",
                id="prompt-directory",
                classes="field-input",
            )

        yield Static("─" * 50, classes="separator")

        # Logging
        yield Static("Logging", classes="section-title")

        with Horizontal(classes="switch-row"):
            yield Label("Save Trajectory", classes="switch-label")
            yield Switch(value=self.settings.save_trajectory, id="save-trajectory")

        yield Static("─" * 50, classes="separator")

        # Tracing
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
            "prompt_directory": self.query_one("#prompt-directory", Input).value.strip(),
            "save_trajectory": self.query_one("#save-trajectory", Switch).value,
            "tracing_enabled": self.query_one("#tracing-enabled", Switch).value,
            "tracing_provider": self.query_one("#tracing-provider", Select).value,
        }
