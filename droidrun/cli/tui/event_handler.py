"""Agent event rendering to LogView."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    from droidrun.cli.tui.widgets.log_view import LogView
    from droidrun.cli.tui.widgets.status_bar import StatusBar


class EventHandler:

    def __init__(self, log: LogView, status_bar: StatusBar) -> None:
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
            self.log.append(f"  \u203a tap  {event.description}")
        elif isinstance(event, SwipeActionEvent):
            self.log.append(f"  \u203a swipe  {event.description}")
        elif isinstance(event, InputTextActionEvent):
            self.log.append(f"  \u203a input  {event.text}")
        elif isinstance(event, ScreenshotEvent):
            self.log.append("  \u203a screenshot")
        elif isinstance(event, ExecutorResultEvent):
            self._step_count += 1
            self.status_bar.current_step = self._step_count

    def reset(self) -> None:
        self._step_count = 0

    def _manager_plan(self, event: ManagerPlanDetailsEvent) -> None:
        if event.plan:
            self.log.append(f"  \u25b8 {event.plan}")
        if event.subgoal:
            self.log.append(f"    \u2192 {event.subgoal}")
        if event.thought:
            self.log.append(f"    {event.thought}")

    def _executor_action(self, event: ExecutorActionEvent) -> None:
        if event.description:
            self.log.append(f"  \u25b8 {event.description}")
        if event.thought:
            self.log.append(f"    {event.thought}")

    def _codeact_response(self, event: CodeActResponseEvent) -> None:
        self._step_count += 1
        self.status_bar.current_step = self._step_count
        if event.thought:
            self.log.append(f"    {event.thought}")
        if event.code:
            self.log.append("  $ code")
            for line in event.code.split("\n"):
                if line.strip():
                    self.log.append(f"    {line}")

    def _codeact_output(self, event: CodeActOutputEvent) -> None:
        if event.output:
            self.log.append(f"  > {event.output}")

    def _codeact_end(self, event: CodeActEndEvent) -> None:
        status = "done" if event.success else "failed"
        self.log.append(
            f"  \u25a0 {status}: {event.reason} ({event.code_executions} runs)"
        )

    def _scripter(self, event: ScripterThinkingEvent) -> None:
        if event.thought:
            self.log.append(f"    {event.thought}")
        if event.code:
            self.log.append("  $ script")
            for line in event.code.split("\n")[:5]:
                if line.strip():
                    self.log.append(f"    {line}")
