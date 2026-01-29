"""Agent tab — per-agent vision toggles and max steps."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Static, Switch

from droidrun.cli.tui.settings.data import SettingsData


class AgentTab(Vertical):
    """Content for the Agent tab pane."""

    DEFAULT_CSS = """
    AgentTab {
        padding: 1 2;
    }
    AgentTab .section-title {
        color: #CAD3F6;
        text-style: bold;
        margin-bottom: 1;
    }
    AgentTab .section-hint {
        color: #47475e;
        margin-bottom: 1;
    }
    AgentTab .switch-row {
        height: auto;
        margin-bottom: 1;
    }
    AgentTab .switch-label {
        width: 14;
        padding-top: 0;
        color: #838BBC;
    }
    AgentTab .field-row {
        height: auto;
        margin-bottom: 1;
    }
    AgentTab .field-label {
        width: 14;
        padding-top: 1;
        color: #838BBC;
    }
    AgentTab .field-input {
        width: 16;
    }
    AgentTab .separator {
        color: #2e2e4a;
        margin: 1 0;
    }
    """

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Static("Vision", classes="section-title")
        yield Static("enable screenshots for each agent", classes="section-hint")

        with Horizontal(classes="switch-row"):
            yield Label("Manager", classes="switch-label")
            yield Switch(value=self.settings.manager_vision, id="vision-manager")

        with Horizontal(classes="switch-row"):
            yield Label("Executor", classes="switch-label")
            yield Switch(value=self.settings.executor_vision, id="vision-executor")

        with Horizontal(classes="switch-row"):
            yield Label("CodeAct", classes="switch-label")
            yield Switch(value=self.settings.codeact_vision, id="vision-codeact")

        yield Static("─" * 50, classes="separator")
        yield Static("Steps", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Max Steps", classes="field-label")
            yield Input(
                value=str(self.settings.max_steps),
                id="max-steps",
                classes="field-input",
            )

    def collect(self) -> dict:
        """Collect current agent settings."""
        return {
            "manager_vision": self.query_one("#vision-manager", Switch).value,
            "executor_vision": self.query_one("#vision-executor", Switch).value,
            "codeact_vision": self.query_one("#vision-codeact", Switch).value,
            "max_steps": self.query_one("#max-steps", Input).value.strip(),
        }
