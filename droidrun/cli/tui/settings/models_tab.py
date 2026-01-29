"""Models tab — default provider/model + per-agent overrides."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Select, Static

from droidrun.cli.tui.settings.data import AGENT_ROLES, PROVIDERS, SettingsData


PROVIDER_OPTIONS = [(p, p) for p in PROVIDERS]


class _AgentRow(Horizontal):
    """A single per-agent override row: label + provider + model."""

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
            value=self._provider if self._provider else Select.BLANK,
            allow_blank=True,
            prompt="default",
            id=f"agent-provider-{self.role}",
        )
        yield Input(
            value=self._model,
            placeholder="default",
            id=f"agent-model-{self.role}",
        )


class ModelsTab(Vertical):
    """Content for the Models tab pane."""

    DEFAULT_CSS = """
    ModelsTab {
        padding: 1 2;
    }
    ModelsTab .section-title {
        color: #CAD3F6;
        text-style: bold;
        margin-bottom: 1;
    }
    ModelsTab .section-hint {
        color: #47475e;
        margin-bottom: 1;
    }
    ModelsTab .field-row {
        height: auto;
        margin-bottom: 1;
    }
    ModelsTab .field-label {
        width: 14;
        padding-top: 1;
        color: #838BBC;
    }
    ModelsTab .field-input {
        width: 1fr;
    }
    ModelsTab .field-select {
        width: 1fr;
    }
    ModelsTab .separator {
        color: #2e2e4a;
        margin: 1 0;
    }
    """

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

        yield Static("─" * 50, classes="separator")
        yield Static("Per-Agent Overrides", classes="section-title")
        yield Static("leave empty to use default", classes="section-hint")

        for role in AGENT_ROLES:
            override = self.settings.agent_llms.get(role)
            yield _AgentRow(
                role=role,
                provider=override.provider if override else "",
                model=override.model if override else "",
            )

    def collect(self) -> dict:
        """Collect current values from the tab."""
        return {
            "default_provider": self.query_one("#default-provider", Select).value,
            "default_model": self.query_one("#default-model", Input).value.strip(),
            "default_temperature": self.query_one("#default-temperature", Input).value.strip(),
            "agent_llms": {
                role: {
                    "provider": self._get_agent_provider(role),
                    "model": self.query_one(f"#agent-model-{role}", Input).value.strip(),
                }
                for role in AGENT_ROLES
            },
        }

    def _get_agent_provider(self, role: str) -> str:
        sel = self.query_one(f"#agent-provider-{role}", Select)
        return str(sel.value) if sel.value != Select.BLANK else ""
