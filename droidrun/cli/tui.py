"""
DroidRun Terminal User Interface
"""

import asyncio
import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button,
    Input,
    Static,
    RichLog,
    Header,
    Footer,
    Checkbox,
    Collapsible,
    Label,
)
from textual.binding import Binding
from rich.text import Text

from droidrun import DroidAgent, ResultEvent
from droidrun.config_manager import DroidrunConfig
from droidrun.agent.droid.events import (
    ManagerPlanEvent,
    ExecutorResultEvent,
    CodeActResultEvent,
)
from droidrun.agent.manager.events import ManagerPlanDetailsEvent
from droidrun.agent.executor.events import ExecutorActionEvent
from droidrun.agent.codeact.events import (
    CodeActResponseEvent,
    CodeActOutputEvent,
    CodeActEndEvent,
)
from droidrun.agent.scripter.events import ScripterThinkingEvent
from droidrun.agent.common.events import (
    TapActionEvent,
    SwipeActionEvent,
    InputTextActionEvent,
    ScreenshotEvent,
)


DROIDRUN_ASCII = """[#CAD3F6]
██████╗ ██████╗  ██████╗ ██╗██████╗ ██████╗ ██╗   ██╗███╗   ██╗
██╔══██╗██╔══██╗██╔═══██╗██║██╔══██╗██╔══██╗██║   ██║████╗  ██║
██║  ██║██████╔╝██║   ██║██║██║  ██║██████╔╝██║   ██║██╔██╗ ██║
██║  ██║██╔══██╗██║   ██║██║██║  ██║██╔══██╗██║   ██║██║╚██╗██║
██████╔╝██║  ██║╚██████╔╝██║██████╔╝██║  ██║╚██████╔╝██║ ╚████║
╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
[/#CAD3F6]

[#838BBC]✨ Try Cloud version to get started with no setup required[/#838BBC]
[link="https://cloud.droidrun.ai"][aqua]cloud.droidrun.ai[/aqua][/link]
"""


class LogCapture(logging.Handler):
    """Custom logging handler that captures logs for TUI display."""

    def __init__(self, log_widget: RichLog):
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record):
        try:
            msg = self.format(record)
            # Map log levels to colors
            level_colors = {
                "DEBUG": "dim",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold red",
            }
            color = level_colors.get(record.levelname, "white")
            self.log_widget.write(Text(msg, style=color))
        except Exception:
            self.handleError(record)


class DroidrunTUI(App):
    """A Textual TUI for DroidRun."""

    CSS = """
    Screen {
        background: #1B1B25;
        align:center middle;

    }
    
    #ascii-header {
        color: $accent;
        text-align: center;
        align:center middle;
        padding: 1;
    }
    
    #ascii-header.hidden {
        display: none;
    }
    
    #settings-panel {
        height: auto;
        border: solid $primary;
        padding: 1;
        background: #1B1B25;
    }
    
    #settings-panel.hidden {
        display: none;
    }
    
    #settings-content {
        height: auto;
        max-height: 30;
    }
    
    .settings-label {
        margin-top: 1;
        color: $accent;
    }
    
    .settings-input {
        margin-bottom: 1;
    }
    
    #settings-buttons {
        height: auto;
        margin-top: 1;
    }
    
    #log-container {
        height: 1fr;
        padding: 1;
    }
    
    #log-container.hidden {
        display: none;
    }
    
    #log-display {
        height: 100%;
        background: $surface-darken-1;
        border: none;
    }
    
    #input-container {
        dock:bottom;
        height: auto;
        padding: 1;
        background: #1B1B25;
    }
    
    #input-container.hidden {
        display: none;
    }
    
    #prompt-input {
        width: 1fr;
        margin-right: 1;
        background:#1B1B25;
        border:solid #47475e;
        margin-bottom:1;
    }
    
    #run-button {
        width: 15;
        min-width: 15;
    }
    
    #settings-button {
        width: 15;
        min-width: 15;
        margin-right: 1;
    }
    
    .status-bar {
        height: 1;
        background: $primary;
        color: $text;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_logs", "Clear Logs", show=True),
        Binding("ctrl+s", "toggle_settings", "Settings", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.running = False
        self.settings_visible = False
        self.logs_visible = False

        # Default settings
        self.device_serial = None
        self.provider = "GoogleGenAI"
        self.model = "models/gemini-2.5-flash"
        self.max_steps = 15
        self.reasoning = False
        self.manager_vision = True
        self.executor_vision = False
        self.codeact_vision = False
        self.save_trajectory = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # ASCII art header
        yield Static(DROIDRUN_ASCII, id="ascii-header")

        # Settings panel (hidden by default)
        with Container(id="settings-panel", classes="hidden"):
            yield Static("⚙️  Settings", classes="settings-label")
            with ScrollableContainer(id="settings-content"):
                yield Label("Device Serial", classes="settings-label")
                yield Input(
                    placeholder="Leave empty for auto-detect",
                    id="device-serial-input",
                    classes="settings-input",
                )

                yield Label("Provider", classes="settings-label")
                yield Input(
                    value="GoogleGenAI",
                    id="provider-input",
                    classes="settings-input",
                )

                yield Label("Model", classes="settings-label")
                yield Input(
                    value="models/gemini-2.5-flash",
                    id="model-input",
                    classes="settings-input",
                )

                yield Label("Max Steps", classes="settings-label")
                yield Input(
                    value="15",
                    id="max-steps-input",
                    classes="settings-input",
                )

                yield Checkbox("Reasoning", id="reasoning-checkbox", value=False)

                with Collapsible(title="Vision Settings", collapsed=False):
                    yield Checkbox(
                        "Manager Vision", id="manager-vision-checkbox", value=True
                    )
                    yield Checkbox(
                        "Executor Vision", id="executor-vision-checkbox", value=False
                    )
                    yield Checkbox(
                        "CodeAct Vision", id="codeact-vision-checkbox", value=False
                    )

                yield Checkbox(
                    "Save Trajectory", id="save-trajectory-checkbox", value=False
                )

            with Horizontal(id="settings-buttons"):
                yield Button(
                    "Save Settings", variant="success", id="save-settings-button"
                )
                yield Button("Cancel", variant="default", id="cancel-settings-button")

        # Log display container (hidden by default)
        with Container(id="log-container", classes="hidden"):
            yield RichLog(id="log-display", wrap=True, highlight=True, markup=True)

        # Input container at bottom
        with Horizontal(id="input-container"):
            yield Button("Settings", variant="primary", id="settings-button")
            yield Input(
                placeholder=">",
                id="prompt-input",
            )
            yield Button("Run", variant="success", id="run-button")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        # Focus the input field
        self.query_one("#prompt-input", Input).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "run-button":
            await self.execute_command()
        elif event.button.id == "settings-button":
            self.toggle_settings()
        elif event.button.id == "save-settings-button":
            self.save_settings()
        elif event.button.id == "cancel-settings-button":
            self.toggle_settings()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        if event.input.id == "prompt-input":
            await self.execute_command()

    def toggle_settings(self) -> None:
        """Toggle settings panel visibility."""
        ascii_header = self.query_one("#ascii-header", Static)
        settings_panel = self.query_one("#settings-panel", Container)
        input_container = self.query_one("#input-container", Horizontal)

        if self.settings_visible:
            # Hide settings, show ASCII header and input container
            settings_panel.add_class("hidden")
            ascii_header.remove_class("hidden")
            input_container.remove_class("hidden")
            self.settings_visible = False
        else:
            # Show settings, hide ASCII header and input container
            ascii_header.add_class("hidden")
            settings_panel.remove_class("hidden")
            input_container.add_class("hidden")
            self.settings_visible = True

    def save_settings(self) -> None:
        """Save settings from the UI."""
        # Get values from inputs
        device_input = self.query_one("#device-serial-input", Input)
        provider_input = self.query_one("#provider-input", Input)
        model_input = self.query_one("#model-input", Input)
        max_steps_input = self.query_one("#max-steps-input", Input)

        # Get checkbox values
        reasoning_checkbox = self.query_one("#reasoning-checkbox", Checkbox)
        manager_vision_checkbox = self.query_one("#manager-vision-checkbox", Checkbox)
        executor_vision_checkbox = self.query_one("#executor-vision-checkbox", Checkbox)
        codeact_vision_checkbox = self.query_one("#codeact-vision-checkbox", Checkbox)
        save_trajectory_checkbox = self.query_one("#save-trajectory-checkbox", Checkbox)

        # Store settings
        self.device_serial = device_input.value.strip() or None
        self.provider = provider_input.value.strip()
        self.model = model_input.value.strip()

        try:
            self.max_steps = int(max_steps_input.value.strip())
        except ValueError:
            self.max_steps = 15

        self.reasoning = reasoning_checkbox.value
        self.manager_vision = manager_vision_checkbox.value
        self.executor_vision = executor_vision_checkbox.value
        self.codeact_vision = codeact_vision_checkbox.value
        self.save_trajectory = save_trajectory_checkbox.value

        # Show confirmation
        log_display = self.query_one("#log-display", RichLog)
        log_display.write(Text("✅ Settings saved!", style="bold green"))

        # Hide settings panel
        self.toggle_settings()

    async def execute_command(self) -> None:
        """Execute the command from the input field."""
        if self.running:
            log_display = self.query_one("#log-display", RichLog)
            log_display.write(Text("⚠️  A command is already running", style="yellow"))
            return

        prompt_input = self.query_one("#prompt-input", Input)
        command = prompt_input.value.strip()

        if not command:
            log_display = self.query_one("#log-display", RichLog)
            log_display.write(Text("⚠️  Please enter a command", style="yellow"))
            return

        # Immediately update UI state before starting execution
        prompt_input.value = ""
        self.running = True
        run_button = self.query_one("#run-button", Button)
        run_button.disabled = True
        prompt_input.disabled = True

        # Show logs panel and hide ASCII header
        log_container = self.query_one("#log-container", Container)
        if not self.logs_visible:
            log_container.remove_class("hidden")
            self.logs_visible = True

        ascii_header = self.query_one("#ascii-header", Static)
        ascii_header.add_class("hidden")

        log_display = self.query_one("#log-display", RichLog)
        log_display.write(Text(f"\n{'='*60}", style="dim"))
        log_display.write(Text(f"📝 Command: {command}", style="bold cyan"))
        log_display.write(Text(f"{'='*60}\n", style="dim"))

        # Force UI refresh before blocking operations
        self.refresh()
        await asyncio.sleep(0)  # Let the UI update

        success = False

        try:
            # Load config
            config = DroidrunConfig()
            config.logging.debug = True  # Enable debug for all logs

            # Apply settings from UI
            if self.device_serial:
                config.device.serial = self.device_serial

            config.agent.max_steps = self.max_steps
            config.agent.reasoning = self.reasoning
            config.agent.manager.vision = self.manager_vision
            config.agent.executor.vision = self.executor_vision
            config.agent.codeact.vision = self.codeact_vision

            if self.save_trajectory:
                config.logging.save_trajectory = "action"
            else:
                config.logging.save_trajectory = "none"

            log_display.write(Text("🚀 Initializing DroidAgent...", style="green"))
            self.refresh()
            await asyncio.sleep(0)

            # Create DroidAgent with LLM config if specified
            droid_kwargs = {"runtype": "tui"}

            # Load custom LLM if provider/model specified
            if self.provider and self.model:
                from droidrun.agent.utils.llm_picker import load_llm

                try:
                    llm = load_llm(
                        provider_name=self.provider,
                        model_name=self.model,
                        temperature=0.0,
                    )
                    droid_kwargs["llms"] = llm
                    log_display.write(
                        Text(f"🤖 Using {self.provider} - {self.model}", style="cyan")
                    )
                except Exception as e:
                    log_display.write(
                        Text(
                            f"⚠️  Could not load LLM: {e}, using default", style="yellow"
                        )
                    )

            # Create DroidAgent
            droid_agent = DroidAgent(
                goal=command,
                config=config,
                timeout=1000,
                **droid_kwargs,
            )

            log_display.write(Text("▶️  Starting execution...\n", style="green"))
            self.refresh()
            await asyncio.sleep(0)

            # Run agent and get handler
            handler = droid_agent.run()

            # Stream events in real-time
            async for event in handler.stream_events():
                # Manager events
                if isinstance(event, ManagerPlanDetailsEvent):
                    if event.plan:
                        log_display.write(Text(f"📋 Plan: {event.plan}", style="cyan"))
                    if event.subgoal:
                        log_display.write(
                            Text(
                                f"🎯 Current subgoal: {event.subgoal}",
                                style="yellow",
                            )
                        )
                    if event.thought:
                        log_display.write(
                            Text(f"💭 Thought: {event.thought}", style="dim")
                        )

                # Executor action events
                elif isinstance(event, ExecutorActionEvent):
                    if event.description:
                        log_display.write(
                            Text(f"⚡ Action: {event.description}", style="green")
                        )
                    if event.thought:
                        log_display.write(
                            Text(f"💭 Thought: {event.thought}", style="dim")
                        )

                # CodeAct response events
                elif isinstance(event, CodeActResponseEvent):
                    if event.thought:
                        log_display.write(
                            Text(f"💭 Thoughts: {event.thought}", style="dim")
                        )
                    if event.code:
                        log_display.write(Text(f"🐍 Code:", style="blue"))
                        for line in event.code.split("\n"):
                            if line.strip():
                                log_display.write(Text(f"  {line}", style="blue dim"))

                # Code execution results
                elif isinstance(event, CodeActOutputEvent):
                    if event.output:
                        log_display.write(
                            Text(f"📤 Execution output: {event.output}", style="white")
                        )

                # CodeAct end event
                elif isinstance(event, CodeActEndEvent):
                    log_display.write(
                        Text(
                            f"✓ CodeAct completed: {event.reason} (executed {event.code_executions} times)",
                            style="cyan",
                        )
                    )

                # Scripter events
                elif isinstance(event, ScripterThinkingEvent):
                    if event.thoughts:
                        log_display.write(
                            Text(f"📜 Scripter: {event.thoughts}", style="magenta dim")
                        )
                    if event.code:
                        log_display.write(Text(f"🐍 Script code:", style="magenta"))
                        for line in event.code.split("\n")[:5]:  # Show first 5 lines
                            if line.strip():
                                log_display.write(
                                    Text(f"  {line}", style="magenta dim")
                                )

                # Action events
                elif isinstance(event, TapActionEvent):
                    log_display.write(
                        Text(f"👆 Tap: {event.description}", style="green")
                    )

                elif isinstance(event, SwipeActionEvent):
                    log_display.write(
                        Text(f"👉 Swipe: {event.description}", style="green")
                    )

                elif isinstance(event, InputTextActionEvent):
                    log_display.write(Text(f"⌨️  Input: {event.text}", style="green"))

                # Screenshot events (just log, don't display image)
                elif isinstance(event, ScreenshotEvent):
                    log_display.write(Text("📸 Screenshot captured", style="dim"))

            # Wait for final result
            result: ResultEvent = await handler
            success = result.success

            log_display.write(
                Text(f"\n📊 Completed in {result.steps} steps", style="cyan")
            )

        except KeyboardInterrupt:
            log_display.write(Text("\n⏹️  Command interrupted by user", style="yellow"))
            success = False

        except Exception as e:
            log_display.write(Text(f"\n💥 Error occurred: {e}", style="bold red"))
            import traceback

            tb = traceback.format_exc()
            # Display traceback line by line for better readability
            for line in tb.split("\n"):
                if line.strip():
                    log_display.write(Text(line, style="red dim"))
            success = False

        finally:
            # Display final result status - keep logs visible
            if success:
                log_display.write(
                    Text("\n✅ Command completed successfully!", style="bold green")
                )
            else:
                log_display.write(
                    Text("\n❌ Command failed or was interrupted", style="bold red")
                )

            log_display.write(Text(f"{'='*60}\n", style="dim"))

            # Re-enable controls - logs remain visible (keep ASCII header hidden)
            self.running = False
            run_button.disabled = False
            prompt_input.disabled = False
            prompt_input.focus()

    def action_clear_logs(self) -> None:
        """Clear the log display."""
        log_display = self.query_one("#log-display", RichLog)
        log_display.clear()
        log_display.write(Text("🧹 Logs cleared", style="dim"))

    def action_toggle_settings(self) -> None:
        """Toggle settings panel visibility."""
        self.toggle_settings()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def run_tui():
    """Run the DroidRun TUI application."""
    app = DroidrunTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
