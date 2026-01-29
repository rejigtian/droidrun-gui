"""Config modal overlay screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Checkbox, Static


class ConfigModal(ModalScreen[dict | None]):

    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(
        self,
        device_serial: str,
        provider: str,
        model: str,
        max_steps: int,
        manager_vision: bool,
        executor_vision: bool,
        codeact_vision: bool,
        save_trajectory: bool,
    ) -> None:
        super().__init__()
        self._device_serial = device_serial
        self._provider = provider
        self._model = model
        self._max_steps = max_steps
        self._manager_vision = manager_vision
        self._executor_vision = executor_vision
        self._codeact_vision = codeact_vision
        self._save_trajectory = save_trajectory

    def compose(self) -> ComposeResult:
        with Vertical(id="config-dialog"):
            yield Static("Configuration", id="config-title")

            with ScrollableContainer(id="config-scroll"):
                yield Label("Connection", classes="config-section")

                yield Label("Device Serial", classes="config-label")
                yield Input(
                    value=self._device_serial,
                    placeholder="auto-detect",
                    id="cfg-device",
                    classes="config-input",
                )

                yield Label("LLM", classes="config-section")

                yield Label("Provider", classes="config-label")
                yield Input(
                    value=self._provider,
                    id="cfg-provider",
                    classes="config-input",
                )

                yield Label("Model", classes="config-label")
                yield Input(
                    value=self._model,
                    id="cfg-model",
                    classes="config-input",
                )

                yield Label("Agent", classes="config-section")

                yield Label("Max Steps", classes="config-label")
                yield Input(
                    value=str(self._max_steps),
                    id="cfg-steps",
                    classes="config-input",
                )

                yield Label("Vision", classes="config-section")
                with Vertical(id="vision-group"):
                    yield Checkbox("Manager", id="cfg-manager-vision", value=self._manager_vision)
                    yield Checkbox("Executor", id="cfg-executor-vision", value=self._executor_vision)
                    yield Checkbox("CodeAct", id="cfg-codeact-vision", value=self._codeact_vision)

                yield Label("Logging", classes="config-section")
                yield Checkbox("Save Trajectory", id="cfg-trajectory", value=self._save_trajectory)

            with Horizontal(id="config-buttons"):
                yield Button("Save", variant="success", id="config-save-btn")
                yield Button("Cancel", variant="default", id="config-cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "config-save-btn":
            self.dismiss(self._collect_values())
        elif event.button.id == "config-cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _collect_values(self) -> dict:
        return {
            "device_serial": self.query_one("#cfg-device", Input).value.strip(),
            "provider": self.query_one("#cfg-provider", Input).value.strip(),
            "model": self.query_one("#cfg-model", Input).value.strip(),
            "max_steps": self.query_one("#cfg-steps", Input).value.strip(),
            "manager_vision": self.query_one("#cfg-manager-vision", Checkbox).value,
            "executor_vision": self.query_one("#cfg-executor-vision", Checkbox).value,
            "codeact_vision": self.query_one("#cfg-codeact-vision", Checkbox).value,
            "save_trajectory": self.query_one("#cfg-trajectory", Checkbox).value,
        }
