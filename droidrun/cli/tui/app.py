"""DroidRun TUI - Main application."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static, RichLog
from rich.text import Text

from droidrun.cli.tui.commands import match_commands, resolve_command
from droidrun.cli.tui.config_modal import ConfigModal
from droidrun.cli.tui.event_handler import EventHandler
from droidrun.cli.tui.widgets import InputBar, CommandDropdown, StatusBar


BANNER = """[#CAD3F6]
\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2557   \u2588\u2588\u2557
\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551
\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551
\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551
\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d
[/#CAD3F6]
[#838BBC]Type a command to get started, or / for commands[/#838BBC]"""


class DroidrunTUI(App):
    """DroidRun Terminal User Interface."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+l", "clear_logs", "Clear Logs", show=False),
        Binding("tab", "toggle_mode", "Toggle Mode", show=False),
        Binding("escape", "handle_esc", "Esc", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self._cancel_requested = False
        self._logs_visible = False
        self._esc_last: float = 0.0

        # Settings (loaded from config on first run)
        self.device_serial: str = ""
        self.provider: str = "GoogleGenAI"
        self.model: str = "models/gemini-2.5-flash"
        self.max_steps: int = 15
        self.reasoning: bool = False
        self.manager_vision: bool = True
        self.executor_vision: bool = False
        self.codeact_vision: bool = False
        self.save_trajectory: bool = False

    def compose(self) -> ComposeResult:
        yield Static(BANNER, id="banner")

        with Container(id="log-container", classes="hidden"):
            yield RichLog(id="log-display", wrap=True, highlight=True, markup=True)

        yield InputBar(placeholder=">", id="input-bar")
        yield CommandDropdown(id="command-dropdown", classes="hidden")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self.query_one("#input-bar", InputBar).focus()
        self._sync_status_bar()

    # ── Status bar sync ──

    def _sync_status_bar(self) -> None:
        status = self.query_one("#status-bar", StatusBar)
        status.device_name = self.device_serial or "no device"
        status.device_connected = bool(self.device_serial)
        status.mode = "reasoning" if self.reasoning else "fast"
        status.max_steps = self.max_steps

    # ── Input handling ──

    def on_input_bar_submitted(self, message: InputBar.Submitted) -> None:
        text = message.value.strip()
        if not text:
            return

        # Hide dropdown if visible
        self._hide_dropdown()

        if text.startswith("/"):
            self._handle_slash_command(text[1:])
        else:
            self.run_worker(self._execute_command(text), exclusive=True)

    def on_input_bar_slash_changed(self, message: InputBar.SlashChanged) -> None:
        commands = match_commands(message.query)
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        dropdown.update_commands(commands)
        self._show_dropdown()

    def on_input_bar_slash_exited(self, message: InputBar.SlashExited) -> None:
        self._hide_dropdown()

    def on_command_dropdown_selected(self, message: CommandDropdown.Selected) -> None:
        # Clear input bar, hide dropdown, execute command
        input_bar = self.query_one("#input-bar", InputBar)
        input_bar.value = ""
        self._hide_dropdown()
        self._handle_slash_command(message.command_name)

    # ── Dropdown visibility ──

    def _show_dropdown(self) -> None:
        self.query_one("#command-dropdown").remove_class("hidden")
        self.query_one("#status-bar").add_class("hidden")

    def _hide_dropdown(self) -> None:
        self.query_one("#command-dropdown").add_class("hidden")
        self.query_one("#status-bar").remove_class("hidden")

    # ── Slash commands ──

    def _handle_slash_command(self, text: str) -> None:
        parts = text.strip().split()
        if not parts:
            return

        cmd_name = parts[0]
        cmd = resolve_command(cmd_name)

        if cmd is None:
            log = self.query_one("#log-display", RichLog)
            self._show_logs()
            log.write(Text(f"  Unknown command: /{cmd_name}", style="#ed8796"))
            return

        handler = getattr(self, cmd.handler, None)
        if handler:
            handler()

    # ── Command handlers ──

    def action_open_config(self) -> None:
        modal = ConfigModal(
            device_serial=self.device_serial,
            provider=self.provider,
            model=self.model,
            max_steps=self.max_steps,
            manager_vision=self.manager_vision,
            executor_vision=self.executor_vision,
            codeact_vision=self.codeact_vision,
            save_trajectory=self.save_trajectory,
        )
        self.push_screen(modal, callback=self._on_config_dismissed)

    def _on_config_dismissed(self, values: dict | None) -> None:
        if values is None:
            return

        self.device_serial = values["device_serial"]
        self.provider = values["provider"]
        self.model = values["model"]
        try:
            self.max_steps = int(values["max_steps"])
        except (ValueError, TypeError):
            pass
        self.manager_vision = values["manager_vision"]
        self.executor_vision = values["executor_vision"]
        self.codeact_vision = values["codeact_vision"]
        self.save_trajectory = values["save_trajectory"]

        self._sync_status_bar()

        if self._logs_visible:
            log = self.query_one("#log-display", RichLog)
            log.write(Text("  settings updated", style="#a6da95"))

    def action_open_device(self) -> None:
        log = self.query_one("#log-display", RichLog)
        self._show_logs()
        log.write(Text("  /device - coming soon", style="#838BBC"))

    def action_clear_logs(self) -> None:
        log = self.query_one("#log-display", RichLog)
        log.clear()

    # ── Bindings ──

    def action_toggle_mode(self) -> None:
        self.reasoning = not self.reasoning
        self._sync_status_bar()

    def action_handle_esc(self) -> None:
        now = time.monotonic()
        double_esc = (now - self._esc_last) < 0.3
        self._esc_last = now

        if self.running and not double_esc:
            # Single esc while running → stop agent
            self._cancel_requested = True
            log = self.query_one("#log-display", RichLog)
            log.write(Text("  stopping agent...", style="#ed8796"))
        elif double_esc:
            # Double esc → clear input
            self.query_one("#input-bar", InputBar).clear_input()

    # ── Log visibility ──

    def _show_logs(self) -> None:
        if not self._logs_visible:
            self.query_one("#log-container").remove_class("hidden")
            self.query_one("#banner").add_class("hidden")
            self._logs_visible = True

    # ── Agent execution ──

    async def _execute_command(self, command: str) -> None:
        if self.running:
            log = self.query_one("#log-display", RichLog)
            log.write(Text("  A command is already running", style="#eed49f"))
            return

        self.running = True
        self._cancel_requested = False
        input_bar = self.query_one("#input-bar", InputBar)
        input_bar.disabled = True

        self._show_logs()

        log = self.query_one("#log-display", RichLog)
        status = self.query_one("#status-bar", StatusBar)

        log.write(Text(f"\n{'=' * 60}", style="#47475e"))
        log.write(Text(f"  {command}", style="bold #CAD3F6"))
        log.write(Text(f"{'=' * 60}\n", style="#47475e"))

        status.is_running = True
        status.current_step = 0

        event_handler = EventHandler(log, status)
        success = False

        try:
            from droidrun import DroidAgent, ResultEvent
            from droidrun.config_manager import ConfigLoader

            config = ConfigLoader.load()
            config.logging.debug = True

            if self.device_serial:
                config.device.serial = self.device_serial
            config.agent.max_steps = self.max_steps
            config.agent.reasoning = self.reasoning
            config.agent.manager.vision = self.manager_vision
            config.agent.executor.vision = self.executor_vision
            config.agent.codeact.vision = self.codeact_vision
            config.logging.save_trajectory = "action" if self.save_trajectory else "none"

            log.write(Text("  initializing agent...", style="#a6da95"))

            droid_kwargs = {"runtype": "tui"}

            if self.provider and self.model:
                from droidrun.agent.utils.llm_picker import load_llm

                try:
                    llm = load_llm(
                        provider_name=self.provider,
                        model_name=self.model,
                        temperature=0.0,
                    )
                    droid_kwargs["llms"] = llm
                    log.write(Text(f"  {self.provider} / {self.model}", style="#838BBC"))
                except Exception as e:
                    log.write(Text(f"  LLM load failed: {e}, using defaults", style="#eed49f"))

            droid_agent = DroidAgent(
                goal=command,
                config=config,
                timeout=1000,
                **droid_kwargs,
            )

            log.write(Text("  running...\n", style="#a6da95"))

            handler = droid_agent.run()

            async for event in handler.stream_events():
                if self._cancel_requested:
                    log.write(Text("\n  agent stopped by user", style="#ed8796"))
                    break
                event_handler.handle(event)

            if not self._cancel_requested:
                result: ResultEvent = await handler
                success = result.success
                log.write(Text(f"\n  completed in {result.steps} steps", style="#8aadf4"))

        except Exception as e:
            log.write(Text(f"\n  error: {e}", style="bold #ed8796"))
            import traceback
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    log.write(Text(f"  {line}", style="#ed8796 dim"))

        finally:
            if success:
                log.write(Text("\n  success", style="bold #a6da95"))
            else:
                log.write(Text("\n  failed", style="bold #ed8796"))
            log.write(Text(f"{'=' * 60}\n", style="#47475e"))

            self.running = False
            self._cancel_requested = False
            status.is_running = False
            input_bar.disabled = False
            input_bar.focus()
