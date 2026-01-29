"""Main settings modal screen with tabbed navigation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, TabbedContent, TabPane

from droidrun.cli.tui.settings.agent_tab import AgentTab
from droidrun.cli.tui.settings.advanced_tab import AdvancedTab
from droidrun.cli.tui.settings.data import SettingsData
from droidrun.cli.tui.settings.models_tab import ModelsTab


class SettingsScreen(ModalScreen[SettingsData | None]):
    """Tabbed settings modal."""

    BINDINGS = [
        ("escape", "cancel", "Close"),
        ("ctrl+c", "handle_ctrl_c", "Quit"),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #settings-dialog {
        width: 80;
        max-width: 95%;
        height: 85%;
        background: #0c0c0f;
        border: round #27272a;
        padding: 1 2;
    }

    #settings-tabs {
        height: 1fr;
    }

    #settings-tabs ContentSwitcher {
        height: 1fr;
    }

    #settings-tabs TabPane {
        height: 100%;
        overflow-y: auto;
        padding: 1 0 0 0;
    }

    #settings-tabs Tabs {
        background: #0c0c0f;
    }

    #settings-tabs Tab {
        color: #52525b;
        background: #0c0c0f;
    }

    #settings-tabs Tab.-active {
        color: #f4f4f5;
    }

    #settings-tabs Underline {
        color: #27272a;
    }

    #settings-tabs Tab:hover {
        color: #a1a1aa;
    }

    #settings-buttons {
        height: auto;
        margin-top: 1;
        padding-top: 1;
        border-top: solid #27272a;
        align: right middle;
    }
    """

    def __init__(self, settings: SettingsData) -> None:
        super().__init__()
        self._settings = settings

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            with TabbedContent(id="settings-tabs"):
                with TabPane("Models", id="tab-models"):
                    yield ModelsTab(self._settings)
                with TabPane("Agent", id="tab-agent"):
                    yield AgentTab(self._settings)
                with TabPane("Advanced", id="tab-advanced"):
                    yield AdvancedTab(self._settings)

            with HorizontalGroup(id="settings-buttons"):
                yield Button("Save", variant="success", id="settings-save-btn")
                yield Button("Cancel", variant="default", id="settings-cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-save-btn":
            self.dismiss(self._collect())
        elif event.button.id == "settings-cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_handle_ctrl_c(self) -> None:
        self.app.action_handle_ctrl_c()

    def _collect(self) -> SettingsData:
        """Collect all tab values into a SettingsData."""
        profiles = self.query_one(ModelsTab).collect()
        agent = self.query_one(AgentTab).collect()
        advanced = self.query_one(AdvancedTab).collect()

        try:
            max_steps = int(agent["max_steps"])
        except (ValueError, TypeError):
            max_steps = self._settings.max_steps

        return SettingsData(
            profiles=profiles,
            agent_prompts=agent.get("agent_prompts", {}),
            manager_vision=agent["manager_vision"],
            executor_vision=agent["executor_vision"],
            codeact_vision=agent["codeact_vision"],
            max_steps=max_steps,
            use_tcp=advanced["use_tcp"],
            save_trajectory=advanced["save_trajectory"],
            trajectory_gifs=advanced["trajectory_gifs"],
            tracing_enabled=advanced["tracing_enabled"],
            tracing_provider=advanced["tracing_provider"],
            langfuse_host=advanced["langfuse_host"],
            langfuse_public_key=advanced["langfuse_public_key"],
            langfuse_secret_key=advanced["langfuse_secret_key"],
            langfuse_screenshots=advanced["langfuse_screenshots"],
            after_sleep_action=advanced["after_sleep_action"],
            wait_for_stable_ui=advanced["wait_for_stable_ui"],
        )
