"""
Event formatter for converting workflow events to frontend-friendly format.

This module formats events from DroidAgent workflows into structured JSON
that can be easily consumed by a web frontend.
"""

import base64
import json
import logging
from typing import Any

from llama_index.core.workflow import StartEvent, StopEvent

from droidrun.agent.codeact.events import (
    EpisodicMemoryEvent,
    TaskEndEvent,
    TaskExecutionEvent,
    TaskExecutionResultEvent,
    TaskInputEvent,
    TaskThinkingEvent,
)
from droidrun.agent.common.events import MacroEvent, RecordUIStateEvent, ScreenshotEvent
from droidrun.agent.droid.events import (
    CodeActExecuteEvent,
    CodeActResultEvent,
    ExecutorInputEvent,
    ExecutorResultEvent,
    FinalizeEvent,
    ManagerInputEvent,
    ManagerPlanEvent,
)
from droidrun.agent.executor.events import ExecutorActionEvent

from droidrun.backend.models import EventType, FormattedEvent

logger = logging.getLogger("droidrun.backend")


class EventFormatter:
    """
    Formats workflow events for frontend consumption.

    This class converts internal workflow events into structured JSON
    with proper typing and formatting for display in a web interface.
    """

    def __init__(self, session_id: str):
        """
        Initialize the event formatter.

        Args:
            session_id: Session ID to attach to all formatted events
        """
        self.session_id = session_id

    def format_event(self, event: Any) -> FormattedEvent | None:
        """
        Format a workflow event for frontend consumption.

        Args:
            event: The workflow event to format

        Returns:
            FormattedEvent or None if event should not be streamed
        """
        # Map event types to formatting methods
        formatters = {
            StartEvent: self._format_start_event,
            StopEvent: self._format_stop_event,
            TaskThinkingEvent: self._format_task_thinking_event,
            TaskExecutionEvent: self._format_task_execution_event,
            TaskExecutionResultEvent: self._format_execution_result_event,
            TaskEndEvent: self._format_task_end_event,
            ScreenshotEvent: self._format_screenshot_event,
            RecordUIStateEvent: self._format_ui_state_event,
            EpisodicMemoryEvent: self._format_episodic_memory_event,
            ManagerPlanEvent: self._format_manager_plan_event,
            ExecutorActionEvent: self._format_executor_action_event,
            ExecutorResultEvent: self._format_executor_result_event,
            FinalizeEvent: self._format_finalize_event,
            # Input events - don't stream these to frontend
            TaskInputEvent: lambda e: None,
            ManagerInputEvent: lambda e: None,
            ExecutorInputEvent: lambda e: None,
            CodeActExecuteEvent: lambda e: None,
            CodeActResultEvent: lambda e: None,
            MacroEvent: lambda e: None,
        }

        # Get formatter for event type
        event_type = type(event)
        formatter = formatters.get(event_type)

        if formatter is None:
            # Unknown event type, log and skip
            logger.debug(f"Unknown event type: {event_type.__name__}")
            return None

        try:
            return formatter(event)
        except Exception as e:
            logger.error(f"Error formatting event {event_type.__name__}: {e}", exc_info=True)
            return self._format_error_event(event, str(e))

    # =========================================================================
    # Event Formatters
    # =========================================================================

    def _format_start_event(self, event: StartEvent) -> FormattedEvent:
        """Format StartEvent."""
        return FormattedEvent(
            event_type=EventType.START,
            session_id=self.session_id,
            data={
                "message": "Agent execution started",
                "goal": getattr(event, "goal", None) or getattr(event, "topic", None),
            },
        )

    def _format_stop_event(self, event: StopEvent) -> FormattedEvent:
        """Format StopEvent."""
        result = event.result if hasattr(event, "result") else {}
        return FormattedEvent(
            event_type=EventType.STOP,
            session_id=self.session_id,
            data={
                "message": "Agent execution completed",
                "result": result,
                "success": result.get("success", False) if isinstance(result, dict) else False,
            },
        )

    def _format_task_thinking_event(self, event: TaskThinkingEvent) -> FormattedEvent:
        """Format TaskThinkingEvent (CodeAct agent thinking)."""
        return FormattedEvent(
            event_type=EventType.LLM_THINKING,
            session_id=self.session_id,
            data={
                "agent": "codeact",
                "thoughts": event.thoughts or "",
                "code": event.code or "",
                "usage": self._format_usage(event.usage) if hasattr(event, "usage") else None,
            },
        )

    def _format_task_execution_event(self, event: TaskExecutionEvent) -> FormattedEvent:
        """Format TaskExecutionEvent."""
        return FormattedEvent(
            event_type=EventType.CODE_EXECUTION,
            session_id=self.session_id,
            data={
                "code": event.code,
                "message": "Executing code...",
            },
        )

    def _format_execution_result_event(
        self, event: TaskExecutionResultEvent
    ) -> FormattedEvent:
        """Format TaskExecutionResultEvent."""
        return FormattedEvent(
            event_type=EventType.EXECUTION_RESULT,
            session_id=self.session_id,
            data={
                "output": event.output,
                "message": "Code execution complete",
            },
        )

    def _format_task_end_event(self, event: TaskEndEvent) -> FormattedEvent:
        """Format TaskEndEvent."""
        return FormattedEvent(
            event_type=EventType.TASK_END,
            session_id=self.session_id,
            data={
                "success": event.success,
                "reason": event.reason,
                "message": "Task ended",
            },
        )

    def _format_screenshot_event(self, event: ScreenshotEvent) -> FormattedEvent:
        """Format ScreenshotEvent."""
        # Convert screenshot bytes to base64 data URI
        screenshot_data = None
        if event.screenshot:
            try:
                # Encode screenshot as base64
                base64_image = base64.b64encode(event.screenshot).decode("utf-8")
                screenshot_data = f"data:image/png;base64,{base64_image}"
            except Exception as e:
                logger.error(f"Error encoding screenshot: {e}")
                screenshot_data = None

        return FormattedEvent(
            event_type=EventType.SCREENSHOT,
            session_id=self.session_id,
            data={
                "image": screenshot_data,
                "message": "Screenshot captured",
            },
        )

    def _format_ui_state_event(self, event: RecordUIStateEvent) -> FormattedEvent:
        """Format RecordUIStateEvent."""
        return FormattedEvent(
            event_type=EventType.UI_STATE,
            session_id=self.session_id,
            data={
                "ui_state": event.ui_state,
                "message": "UI state recorded",
            },
        )

    def _format_episodic_memory_event(self, event: EpisodicMemoryEvent) -> FormattedEvent:
        """Format EpisodicMemoryEvent."""
        memory_data = None
        if hasattr(event, "episodic_memory") and event.episodic_memory:
            memory = event.episodic_memory
            memory_data = {
                "persona_name": memory.persona.name if hasattr(memory, "persona") else None,
                "steps_count": len(memory.steps) if hasattr(memory, "steps") else 0,
            }

        return FormattedEvent(
            event_type=EventType.EPISODIC_MEMORY,
            session_id=self.session_id,
            data={
                "memory": memory_data,
                "message": "Episodic memory updated",
            },
        )

    def _format_manager_plan_event(self, event: ManagerPlanEvent) -> FormattedEvent:
        """Format ManagerPlanEvent."""
        return FormattedEvent(
            event_type=EventType.MANAGER_PLAN,
            session_id=self.session_id,
            data={
                "agent": "manager",
                "plan": event.plan,
                "current_subgoal": event.current_subgoal,
                "completed_plan": event.completed_plan,
                "thought": event.thought,
                "answer": event.manager_answer if hasattr(event, "manager_answer") else None,
                "message": "Manager created plan",
            },
        )

    def _format_executor_action_event(self, event: ExecutorActionEvent) -> FormattedEvent:
        """Format ExecutorActionEvent."""
        # Parse action JSON
        action_dict = None
        try:
            action_dict = json.loads(event.action_json) if isinstance(event.action_json, str) else event.action_json
        except json.JSONDecodeError:
            action_dict = {"raw": event.action_json}

        return FormattedEvent(
            event_type=EventType.EXECUTOR_ACTION,
            session_id=self.session_id,
            data={
                "agent": "executor",
                "action": action_dict,
                "thought": event.thought,
                "description": event.description,
                "message": f"Executor selected action: {event.description}",
            },
        )

    def _format_executor_result_event(self, event: ExecutorResultEvent) -> FormattedEvent:
        """Format ExecutorResultEvent."""
        return FormattedEvent(
            event_type=EventType.EXECUTOR_ACTION,
            session_id=self.session_id,
            data={
                "agent": "executor",
                "action": event.action,
                "outcome": event.outcome,
                "error": event.error,
                "summary": event.summary,
                "message": f"Action {'succeeded' if event.outcome else 'failed'}: {event.summary}",
            },
        )

    def _format_finalize_event(self, event: FinalizeEvent) -> FormattedEvent:
        """Format FinalizeEvent."""
        return FormattedEvent(
            event_type=EventType.FINALIZE,
            session_id=self.session_id,
            data={
                "success": event.success,
                "reason": event.reason,
                "output": event.output,
                "steps": event.steps if hasattr(event, "steps") else None,
                "tasks": [
                    {"agent_type": t.agent_type, "description": t.description}
                    for t in event.task
                ]
                if hasattr(event, "task") and event.task
                else [],
                "message": "Agent execution finalized",
            },
        )

    def _format_error_event(self, event: Any, error: str) -> FormattedEvent:
        """Format error event."""
        return FormattedEvent(
            event_type=EventType.ERROR,
            session_id=self.session_id,
            data={
                "error": error,
                "event_type": type(event).__name__,
                "message": f"Error formatting event: {error}",
            },
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_usage(self, usage: Any) -> dict[str, Any] | None:
        """Format LLM usage information."""
        if usage is None:
            return None

        if isinstance(usage, dict):
            return usage

        # Handle different usage object types
        usage_dict = {}
        if hasattr(usage, "prompt_tokens"):
            usage_dict["prompt_tokens"] = usage.prompt_tokens
        if hasattr(usage, "completion_tokens"):
            usage_dict["completion_tokens"] = usage.completion_tokens
        if hasattr(usage, "total_tokens"):
            usage_dict["total_tokens"] = usage.total_tokens

        return usage_dict if usage_dict else None

    def format_status_update(self, message: str, current_step: int = None) -> FormattedEvent:
        """
        Create a status update event.

        Args:
            message: Status message
            current_step: Current step number

        Returns:
            FormattedEvent with status update
        """
        return FormattedEvent(
            event_type=EventType.STATUS,
            session_id=self.session_id,
            data={
                "message": message,
                "current_step": current_step,
            },
        )
