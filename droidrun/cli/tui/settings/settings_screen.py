"""Main settings modal screen with tabbed navigation."""

from __future__ import annotations

from copy import deepcopy

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TabbedContent, TabPane

from droidrun.cli.tui.settings.agent_tab import AgentTab
from droidrun.cli.tui.settings.advanced_tab import AdvancedTab
from droidrun.cli.tui.settings.data import LLMSettings, SettingsData
from droidrun.cli.tui.settings.keys_tab import KeysTab
from droidrun.cli.tui.settings.models_tab import ModelsTab


class SettingsScreen(ModalScreen[SettingsData | None]):
    """Tabbed settings modal."""

    BINDINGS = [("escape", "cancel", "Close")]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }

    #settings-dialog {
        width: 80;
        max-width: 95%;
        height: auto;
        max-height: 85%;
        background: #1B1B25;
        border: round #838BBC;
        padding: 1 2;
    }

    #settings-title {
        text-align: center;
        text-style: bold;
        color: #CAD3F6;
        padding-bottom: 1;
        border-bottom: solid #2e2e4a;
        margin-bottom: 1;
    }

    #settings-tabs {
        height: auto;
        max-height: 70%;
    }

    #settings-buttons {
        height: auto;
        margin-top: 1;
        padding-top: 1;
        border-top: solid #2e2e4a;
        align: right middle;
    }

    #settings-save-btn {
        margin-right: 1;
    }

    /* Tab styling overrides */
    #settings-tabs ContentSwitcher {
        height: auto;
    }
    #settings-tabs TabPane {
        height: auto;
        padding: 0;
    }
    #settings-tabs Tabs {
        background: #1B1B25;
    }
    #settings-tabs Tab {
        color: #838BBC;
        background: #1B1B25;
    }
    #settings-tabs Tab.-active {
        color: #CAD3F6;
    }
    #settings-tabs Underline {
        color: #838BBC;
    }
    #settings-tabs Tab:hover {
        color: #CAD3F6;
    }
    """

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self._settings = settings

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Static("Settings", id="settings-title")

            with TabbedContent(id="settings-tabs"):
                with TabPane("Models", id="tab-models"):
                    yield ModelsTab(self._settings)
                with TabPane("Keys", id="tab-keys"):
                    yield KeysTab(self._settings)
                with TabPane("Agent", id="tab-agent"):
                    yield AgentTab(self._settings)
                with TabPane("Advanced", id="tab-advanced"):
                    yield AdvancedTab(self._settings)

            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="success", id="settings-save-btn")
                yield Button("Cancel", variant="default", id="settings-cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-save-btn":
            self.dismiss(self._collect())
        elif event.button.id == "settings-cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _collect(self) -> SettingsData:
        """Collect all tab values into a SettingsData."""
        models = self.query_one(ModelsTab).collect()
        keys = self.query_one(KeysTab).collect()
        agent = self.query_one(AgentTab).collect()
        advanced = self.query_one(AdvancedTab).collect()

        # Parse temperature
        try:
            default_temp = float(models["default_temperature"])
        except (ValueError, TypeError):
            default_temp = self._settings.default_temperature

        # Parse max steps
        try:
            max_steps = int(agent["max_steps"])
        except (ValueError, TypeError):
            max_steps = self._settings.max_steps

        # Build per-agent LLM overrides
        agent_llms: dict[str, LLMSettings] = {}
        for role, data in models["agent_llms"].items():
            agent_llms[role] = LLMSettings(
                provider=data["provider"],
                model=data["model"],
            )

        return SettingsData(
            default_provider=models["default_provider"],
            default_model=models["default_model"],
            default_temperature=default_temp,
            agent_llms=agent_llms,
            api_keys=keys["api_keys"],
            base_url=keys["base_url"],
            manager_vision=agent["manager_vision"],
            executor_vision=agent["executor_vision"],
            codeact_vision=agent["codeact_vision"],
            max_steps=max_steps,
            use_tcp=advanced["use_tcp"],
            prompt_directory=advanced["prompt_directory"],
            save_trajectory=advanced["save_trajectory"],
            tracing_enabled=advanced["tracing_enabled"],
            tracing_provider=advanced["tracing_provider"],
        )
