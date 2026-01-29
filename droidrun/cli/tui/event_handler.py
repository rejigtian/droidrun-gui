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
            self.log.write(Text(f"  › tap  {event.description}", style="#4ade80"))
        elif isinstance(event, SwipeActionEvent):
            self.log.write(Text(f"  › swipe  {event.description}", style="#4ade80"))
        elif isinstance(event, InputTextActionEvent):
            self.log.write(Text(f"  › input  {event.text}", style="#4ade80"))
        elif isinstance(event, ScreenshotEvent):
            self.log.write(Text("  › screenshot", style="#3f3f46"))
        elif isinstance(event, ExecutorResultEvent):
            self._step_count += 1
            self.status_bar.current_step = self._step_count

    def reset(self) -> None:
        self._step_count = 0

    def _manager_plan(self, event: ManagerPlanDetailsEvent) -> None:
        if event.plan:
            self.log.write(Text(f"  ▸ {event.plan}", style="#60a5fa"))
        if event.subgoal:
            self.log.write(Text(f"    → {event.subgoal}", style="#facc15"))
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#52525b"))

    def _executor_action(self, event: ExecutorActionEvent) -> None:
        if event.description:
            self.log.write(Text(f"  ▸ {event.description}", style="#4ade80"))
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#52525b"))

    def _codeact_response(self, event: CodeActResponseEvent) -> None:
        self._step_count += 1
        self.status_bar.current_step = self._step_count
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#52525b"))
        if event.code:
            self.log.write(Text("  $ code", style="#60a5fa"))
            for line in event.code.split("\n"):
                if line.strip():
                    self.log.write(Text(f"    {line}", style="#60a5fa dim"))

    def _codeact_output(self, event: CodeActOutputEvent) -> None:
        if event.output:
            self.log.write(Text(f"  > {event.output}", style="#f4f4f5"))

    def _codeact_end(self, event: CodeActEndEvent) -> None:
        style = "#4ade80" if event.success else "#f87171"
        status = "done" if event.success else "failed"
        self.log.write(
            Text(f"  ■ {status}: {event.reason} ({event.code_executions} runs)", style=style)
        )

    def _scripter(self, event: ScripterThinkingEvent) -> None:
        if event.thought:
            self.log.write(Text(f"    {event.thought}", style="#c084fc dim"))
        if event.code:
            self.log.write(Text("  $ script", style="#c084fc"))
            for line in event.code.split("\n")[:5]:
                if line.strip():
                    self.log.write(Text(f"    {line}", style="#c084fc dim"))
