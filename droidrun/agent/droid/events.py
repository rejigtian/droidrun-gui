"""
DroidAgent coordination events.

These events route between DroidAgent and child agents.
For internal agent events, see each agent's events.py file.
"""

from typing import Dict, List, Optional

from llama_index.core.workflow import Event, StopEvent
from pydantic import BaseModel


class FastAgentExecuteEvent(Event):
    instruction: str


class FastAgentResultEvent(Event):
    success: bool
    reason: str
    instruction: str


# ============================================================================
# Manager/Executor coordination events
# ============================================================================


class ManagerInputEvent(Event):
    """Trigger Manager workflow for planning"""

    pass


class ManagerPlanEvent(Event):
    """
    Coordination event from ManagerAgent to DroidAgent.

    Used for workflow step routing only (NOT streamed to frontend).
    For internal events with memory_update metadata, see ManagerPlanDetailsEvent.
    """

    plan: str
    current_subgoal: str
    thought: str
    answer: str = ""
    success: Optional[bool] = None  # True/False if complete, None if in progress


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution"""

    current_subgoal: str


class ExecutorResultEvent(Event):
    """Executor finished with action result."""

    action: Dict
    outcome: bool
    error: str
    summary: str


# ============================================================================
# Script executor coordination events
# ============================================================================


class ScripterExecutorInputEvent(Event):
    """Trigger ScripterAgent workflow for off-device operations"""

    task: str


class ScripterExecutorResultEvent(Event):
    """Scripter finished."""

    task: str
    message: str
    success: bool
    code_executions: int


# ============================================================================
# TEXT MANIPULATOR WORKFLOW EVENTS
# ============================================================================


class TextManipulatorInputEvent(Event):
    """Trigger TextManipulatorAgent workflow for text manipulation"""

    task: str


class TextManipulatorResultEvent(Event):
    task: str
    text_to_type: str
    code_ran: str


# ============================================================================
# EXTERNAL USER MESSAGE EVENTS
# ============================================================================


class ExternalUserMessageEvent(Event):
    """Sent by the caller to inject a user message into the running agent loop.

    Usage::

        handler = agent.run()
        await handler.send_event(
            ExternalUserMessageEvent(message="Actually use Chrome"),
            step="ingest_external_user_message",
        )

    The message is queued in shared state and drained at the next safe
    checkpoint (after tool results in direct mode, or at Manager's
    prepare_context in reasoning mode).
    """

    message: str


class ExternalUserMessageQueuedEvent(Event):
    """Streamed to the caller when an external message is accepted into the queue."""

    message_id: str
    message: str
    queue_length: int
    step_number: int


class ExternalUserMessageAppliedEvent(Event):
    """Streamed when queued external messages are drained into the agent loop."""

    message_ids: List[str]
    consumer: str  # "fast_agent" or "manager"
    step_number: int


class ExternalUserMessageDroppedEvent(Event):
    """Streamed when queued messages are dropped without being processed."""

    message_ids: List[str]
    reason: str  # e.g. "max_steps_reached"
    step_number: int


# ============================================================================
# FINALIZATION EVENTS
# ============================================================================


class FinalizeEvent(Event):
    """Trigger finalization."""

    success: bool
    reason: str


class ResultEvent(StopEvent):
    """
    Final result from DroidAgent.

    Returned by DroidAgent.run() with:
    - success: Whether the task completed successfully
    - reason: Explanation or answer
    - steps: Number of steps taken
    - structured_output: Extracted structured data (if output_model was provided)
    """

    success: bool
    reason: str
    steps: int
    structured_output: Optional[BaseModel] = None
