"""Models tab — default provider/model + per-agent overrides."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Rule, Select, Static

from droidrun.cli.tui.settings.data import AGENT_ROLES, PROVIDERS, SettingsData


PROVIDER_OPTIONS = [(p, p) for p in PROVIDERS]


class _AgentRow(Horizontal):
    """A single per-agent row: label + provider + model."""

    DEFAULT_CSS = """
    _AgentRow {
        height: auto;
        margin-bottom: 1;
    }
    _AgentRow .agent-label {
        width: 12;
        padding-top: 1;
        color: #838BBC;
    }
    _AgentRow Select {
        width: 20;
        margin-right: 1;
    }
    _AgentRow Input {
        width: 1fr;
    }
    """

    def __init__(self, role: str, provider: str, model: str) -> None:
        super().__init__()
        self.role = role
        self._provider = provider
        self._model = model

    def compose(self) -> ComposeResult:
        yield Label(self.role.title(), classes="agent-label")
        yield Select(
            PROVIDER_OPTIONS,
            value=self._provider,
            allow_blank=False,
            id=f"agent-provider-{self.role}",
        )
        yield Input(
            value=self._model,
            id=f"agent-model-{self.role}",
        )


class ModelsTab(Vertical):
    """Content for the Models tab pane."""

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Static("Default", classes="section-title")

        with Horizontal(classes="field-row"):
            yield Label("Provider", classes="field-label")
            yield Select(
                PROVIDER_OPTIONS,
                value=self.settings.default_provider,
                allow_blank=False,
                id="default-provider",
                classes="field-select",
            )

        with Horizontal(classes="field-row"):
            yield Label("Model", classes="field-label")
            yield Input(
                value=self.settings.default_model,
                id="default-model",
                classes="field-input",
            )

        with Horizontal(classes="field-row"):
            yield Label("Temperature", classes="field-label")
            yield Input(
                value=str(self.settings.default_temperature),
                id="default-temperature",
                classes="field-input",
            )

        yield Rule()
        yield Static("Per-Agent", classes="section-title")

        for role in AGENT_ROLES:
            override = self.settings.agent_llms.get(role)
            yield _AgentRow(
                role=role,
                provider=override.provider if override else self.settings.default_provider,
                model=override.model if override else self.settings.default_model,
            )

    def collect(self) -> dict:
        """Collect current values from the tab."""
        return {
            "default_provider": self.query_one("#default-provider", Select).value,
            "default_model": self.query_one("#default-model", Input).value.strip(),
            "default_temperature": self.query_one("#default-temperature", Input).value.strip(),
            "agent_llms": {
                role: {
                    "provider": str(self.query_one(f"#agent-provider-{role}", Select).value),
                    "model": self.query_one(f"#agent-model-{role}", Input).value.strip(),
                }
                for role in AGENT_ROLES
            },
        }
