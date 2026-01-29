"""Agent event rendering to RichLog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from droidrun.agent.manager.events import ManagerPlanDetailsEvent
from droidrun.agent.executor.events import ExecutorActionEvent
from droidrun.agent.droid.events import ExecutorResultEvent, CodeActResultEvent
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

if TYPE_CHECKING:
    from textual.widgets import RichLog
    from droidrun.cli.tui.widgets.status_bar import StatusBar


class EventHandler:

    def __init__(self, log: RichLog, status_bar: StatusBar) -> None:
        self.log = log
        self.status_bar = status_bar
        self._step_count = 0

    def handle(self, event) -> None:
        if isinstance(event, ManagerPlanDetailsEvent):
            self._manager_plan(event)
        elif isinstance(event, ExecutorActionEvent):
            self._executor_action(event)
        elif isinstance(event, CodeActResponseEvent):
            self._codeact_response(event)
        elif isinstance(event, CodeActOutputEvent):
            self._codeact_output(event)
        elif isinstance(event, CodeActEndEvent):
            self._codeact_end(event)
        elif isinstance(event, ScripterThinkingEvent):
            self._scripter(event)
        elif isinstance(event, TapActionEvent):
            self.log.write(Text(f"  \u203a tap  {event.description}", style="#a6da95"))
        elif isinstance(event, SwipeActionEvent):
            self.log.write(Text(f"  \u203a swipe  {event.description}", style="#a6da95"))
        elif isinstance(event, InputTextActionEvent):
            self.log.write(Text(f"  \u203a input  {event.text}", style="#a6da95"))
        elif isinstance(event, ScreenshotEvent):
            self.log.write(Text("  \u203a screenshot", style="#47475e"))
        elif isinstance(event, ExecutorResultEvent):
            self._step_count += 1
            self.status_bar.current_step = self._step_count

    def reset(self) -> None:
        self._step_count = 0

    def _manager_plan(self, event: ManagerPlanDetailsEvent) -> None:
        if event.plan:
            self.log.write(Text(f"  \u25b8 {event.plan}", style="#8aadf4"))
        if event.subgoal:
            self.log.write(Text(f"    \u2192 {event.subgoal}", style="#eed49f"))
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#47475e"))

    def _executor_action(self, event: ExecutorActionEvent) -> None:
        if event.description:
            self.log.write(Text(f"  \u25b8 {event.description}", style="#a6da95"))
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#47475e"))

    def _codeact_response(self, event: CodeActResponseEvent) -> None:
        self._step_count += 1
        self.status_bar.current_step = self._step_count
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#47475e"))
        if event.code:
            self.log.write(Text("  $ code", style="#8aadf4"))
            for line in event.code.split("\n"):
                if line.strip():
                    self.log.write(Text(f"    {line}", style="#8aadf4 dim"))

    def _codeact_output(self, event: CodeActOutputEvent) -> None:
        if event.output:
            self.log.write(Text(f"  > {event.output}", style="#cad3f5"))

    def _codeact_end(self, event: CodeActEndEvent) -> None:
        style = "#a6da95" if event.success else "#ed8796"
        status = "done" if event.success else "failed"
        self.log.write(
            Text(f"  \u25a0 {status}: {event.reason} ({event.code_executions} runs)", style=style)
        )

    def _scripter(self, event: ScripterThinkingEvent) -> None:
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#c6a0f6 dim"))
        if event.code:
            self.log.write(Text("  $ script", style="#c6a0f6"))
            for line in event.code.split("\n")[:5]:
                if line.strip():
                    self.log.write(Text(f"    {line}", style="#c6a0f6 dim"))
