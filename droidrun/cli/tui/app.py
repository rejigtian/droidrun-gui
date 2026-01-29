"""DroidRun TUI - Main application."""

from __future__ import annotations

import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Static, RichLog
from textual import events
from rich.text import Text

from droidrun.cli.tui.commands import match_commands, resolve_command
from droidrun.cli.tui.event_handler import EventHandler
from droidrun.cli.tui.settings import SettingsData, SettingsScreen
from droidrun.cli.tui.widgets import InputBar, CommandDropdown, StatusBar


BANNER = """[#CAD3F6]
\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2557   \u2588\u2588\u2557
\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551
\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551
\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551
\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d
[/#CAD3F6]
[#838BBC]Type a command or [bold]/[/bold] for options[/#838BBC]"""


class DroidrunTUI(App):

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+l", "clear_logs", "Clear Logs", show=False),
        Binding("escape", "handle_esc", "Esc", show=False),
        Binding("ctrl+c", "handle_ctrl_c", "Quit", show=False),
        Binding("ctrl+z", "quit", "Quit", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self._cancel_requested = False
        self._logs_visible = False
        self._dropdown_visible = False
        self._esc_last: float = 0.0
        self._ctrl_c_last: float = 0.0

        self.reasoning: bool = False

        # Load settings from user config
        try:
            from droidrun.config_manager import ConfigLoader
            config = ConfigLoader.load()
            self.settings = SettingsData.from_config(config)
        except Exception:
            self.settings = SettingsData()

    def compose(self) -> ComposeResult:
        yield Static(BANNER, id="banner")

        with Container(id="log-container", classes="hidden"):
            yield RichLog(id="log-display", wrap=True, highlight=True, markup=True)

        with Vertical(id="bottom-area"):
            yield InputBar(
                placeholder="Type a command or / for options",
                id="input-bar",
            )
            yield CommandDropdown(id="command-dropdown", classes="hidden")
            yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self.query_one("#input-bar", InputBar).focus()
        self._sync_status_bar()
        self._update_hint()

    def on_text_selected(self, event: events.TextSelected) -> None:
        text = self.screen.get_selected_text()
        if text:
            self.copy_to_clipboard(text)
            self.notify("Copied", timeout=1.5)

    def on_key(self, event: events.Key) -> None:
        input_bar = self.query_one("#input-bar", InputBar)
        if not input_bar.has_focus and event.is_printable:
            input_bar.focus()

    # ── Status bar ──

    def _sync_status_bar(self) -> None:
        status = self.query_one("#status-bar", StatusBar)
        # Show model name from first profile in status bar
        first_profile = next(iter(self.settings.profiles.values()), None)
        if first_profile:
            model_display = first_profile.model
            if "/" in model_display:
                model_display = model_display.rsplit("/", 1)[-1]
        else:
            model_display = "no model"
        status.device_name = model_display
        status.device_connected = True
        status.mode = "reasoning" if self.reasoning else "fast"
        status.max_steps = self.settings.max_steps

    def _update_hint(self) -> None:
        status = self.query_one("#status-bar", StatusBar)
        if self.running:
            status.hint = "esc to stop"
        else:
            status.hint = ""

    # ── Input messages ──

    def on_input_bar_submitted(self, message: InputBar.Submitted) -> None:
        text = message.value.strip()
        if not text:
            return

        self._hide_dropdown()

        if text.startswith("/"):
            self._handle_slash_command(text[1:])
        else:
            self.run_worker(self._execute_command(text), exclusive=True)

    def on_input_bar_slash_changed(self, message: InputBar.SlashChanged) -> None:
        commands = match_commands(message.query)
        if not commands:
            self._hide_dropdown()
            return
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        dropdown.update_commands(commands)
        self._show_dropdown()

    def on_input_bar_slash_exited(self, message: InputBar.SlashExited) -> None:
        self._hide_dropdown()

    def on_input_bar_slash_select(self, message: InputBar.SlashSelect) -> None:
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        if dropdown.has_commands:
            dropdown.select_highlighted()

    def on_input_bar_slash_navigate(self, message: InputBar.SlashNavigate) -> None:
        dropdown = self.query_one("#command-dropdown", CommandDropdown)
        dropdown.move_highlight(message.direction)

    def on_input_bar_tab_pressed(self, message: InputBar.TabPressed) -> None:
        if self._dropdown_visible:
            dropdown = self.query_one("#command-dropdown", CommandDropdown)
            if dropdown.has_commands:
                cmd = dropdown._commands[dropdown.highlighted]
                input_bar = self.query_one("#input-bar", InputBar)
                input_bar.value = f"/{cmd.name}"
                input_bar.cursor_position = len(input_bar.value)
        else:
            self.reasoning = not self.reasoning
            self._sync_status_bar()

    def on_command_dropdown_selected(self, message: CommandDropdown.Selected) -> None:
        input_bar = self.query_one("#input-bar", InputBar)
        input_bar.value = ""
        self._hide_dropdown()
        self._handle_slash_command(message.command_name)

    # ── Dropdown visibility ──

    def _show_dropdown(self) -> None:
        self.query_one("#command-dropdown").remove_class("hidden")
        self.query_one("#status-bar").add_class("hidden")
        self._dropdown_visible = True
        self.query_one("#input-bar", InputBar).slash_mode = True

    def _hide_dropdown(self) -> None:
        self.query_one("#command-dropdown").add_class("hidden")
        self.query_one("#status-bar").remove_class("hidden")
        self._dropdown_visible = False
        self.query_one("#input-bar", InputBar).slash_mode = False

    # ── Slash commands ──

    def _handle_slash_command(self, text: str) -> None:
        parts = text.strip().split()
        if not parts:
            return

        cmd = resolve_command(parts[0])

        if cmd is None:
            self._show_logs()
            log = self.query_one("#log-display", RichLog)
            log.write(Text(f"  unknown command: /{parts[0]}", style="#ed8796"))
            return

        handler = getattr(self, cmd.handler, None)
        if handler:
            handler()

    # ── Command handlers ──

    def action_open_config(self) -> None:
        modal = SettingsScreen(self.settings)
        self.push_screen(modal, callback=self._on_settings_dismissed)

    def _on_settings_dismissed(self, result: SettingsData | None) -> None:
        if result is None:
            return

        self.settings = result
        self.settings.save()
        self._sync_status_bar()

        if self._logs_visible:
            log = self.query_one("#log-display", RichLog)
            log.write(Text("  settings updated", style="#a6da95"))

    def action_open_device(self) -> None:
        self._show_logs()
        log = self.query_one("#log-display", RichLog)
        log.write(Text("  /device \u2014 coming soon", style="#838BBC"))

    def action_clear_logs(self) -> None:
        log = self.query_one("#log-display", RichLog)
        log.clear()
        self.query_one("#log-container").add_class("hidden")
        self.query_one("#banner").remove_class("hidden")
        self._logs_visible = False

    # ── Esc handling ──

    def action_handle_esc(self) -> None:
        now = time.monotonic()
        double_esc = (now - self._esc_last) < 0.3
        self._esc_last = now

        if self.running and not double_esc:
            self._cancel_requested = True
            log = self.query_one("#log-display", RichLog)
            log.write(Text("  stopping...", style="#ed8796"))
        elif double_esc:
            self.query_one("#input-bar", InputBar).clear_input()

    def action_handle_ctrl_c(self) -> None:
        now = time.monotonic()
        if (now - self._ctrl_c_last) < 1.5:
            self.exit()
        else:
            self._ctrl_c_last = now
            status = self.query_one("#status-bar", StatusBar)
            status.hint = "ctrl+c again to quit"
            self.set_timer(1.5, self._reset_ctrl_c_hint)

    def _reset_ctrl_c_hint(self) -> None:
        if (time.monotonic() - self._ctrl_c_last) >= 1.0:
            self._update_hint()

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
            log.write(Text("  already running", style="#eed49f"))
            return

        self.running = True
        self._cancel_requested = False
        input_bar = self.query_one("#input-bar", InputBar)
        input_bar.disabled = True
        self._update_hint()

        self._show_logs()

        log = self.query_one("#log-display", RichLog)
        status = self.query_one("#status-bar", StatusBar)

        log.write(Text(f"\n\u2500\u2500 {command} ", style="bold #CAD3F6"))
        log.write(Text(""))

        status.is_running = True
        status.current_step = 0

        event_handler = EventHandler(log, status)
        success = False

        try:
            from droidrun import DroidAgent, ResultEvent
            from droidrun.config_manager import ConfigLoader

            config = ConfigLoader.load()
            config.logging.debug = True

            # Apply settings to config
            self.settings.apply_to_config(config)

            config.agent.reasoning = self.reasoning

            log.write(Text("  initializing...", style="#47475e"))
            first_profile = next(iter(self.settings.profiles.values()), None)
            if first_profile:
                log.write(Text(
                    f"  {first_profile.provider} \u2022 {first_profile.model}",
                    style="#47475e",
                ))

            # DroidAgent loads LLMs from config.llm_profiles via load_agent_llms
            droid_agent = DroidAgent(
                goal=command,
                config=config,
                timeout=1000,
                runtype="tui",
            )

            log.write(Text(""))

            handler = droid_agent.run()

            async for event in handler.stream_events():
                if self._cancel_requested:
                    log.write(Text("\n  stopped by user", style="#ed8796"))
                    break
                event_handler.handle(event)

            if not self._cancel_requested:
                result: ResultEvent = await handler
                success = result.success
                log.write(Text(f"\n  {result.steps} steps", style="#47475e"))

        except Exception as e:
            log.write(Text(f"\n  error: {e}", style="#ed8796"))
            import traceback
            for line in traceback.format_exc().split("\n"):
                if line.strip():
                    log.write(Text(f"  {line}", style="#ed8796 dim"))

        finally:
            if success:
                log.write(Text("  done", style="#a6da95"))
            else:
                log.write(Text("  failed", style="#ed8796"))
            log.write(Text(""))

            self.running = False
            self._cancel_requested = False
            status.is_running = False
            input_bar.disabled = False
            input_bar.focus()
            self._update_hint()
