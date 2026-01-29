"""Agent tab — vision, max steps, per-agent prompt paths."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Rule, Static, Switch

from droidrun.cli.tui.settings.data import AGENT_ROLES, SettingsData


class AgentTab(Vertical):
    """Content for the Agent tab pane."""

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

        yield Rule()
        yield Static("Steps", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Max Steps", classes="field-label")
            yield Input(
                value=str(self.settings.max_steps),
                id="max-steps",
                classes="field-input",
            )

        yield Rule()
        yield Static("Prompts", classes="section-title")
        yield Static("system prompt path per agent", classes="section-hint")

        for role in AGENT_ROLES:
            with Horizontal(classes="field-row"):
                yield Label(role.title(), classes="field-label")
                yield Input(
                    value=self.settings.agent_prompts.get(role, ""),
                    id=f"prompt-{role}",
                    classes="field-input",
                )

    def collect(self) -> dict:
        """Collect current agent settings."""
        return {
            "manager_vision": self.query_one("#vision-manager", Switch).value,
            "executor_vision": self.query_one("#vision-executor", Switch).value,
            "codeact_vision": self.query_one("#vision-codeact", Switch).value,
            "max_steps": self.query_one("#max-steps", Input).value.strip(),
            "agent_prompts": {
                role: self.query_one(f"#prompt-{role}", Input).value.strip()
                for role in AGENT_ROLES
            },
        }
