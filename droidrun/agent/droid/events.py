"""
DroidAgent coordination events.

These events are used for WORKFLOW COORDINATION between DroidAgent and its child agents.
They carry minimal data needed for routing workflow steps.

For internal events with full debugging metadata, see:
- manager/events.py (ManagerInternalPlanEvent)
- executor/events.py (ExecutorInternalActionEvent, ExecutorInternalResultEvent)
- codeact/events.py (Task*, EpisodicMemoryEvent)
"""

import asyncio
from typing import Dict, List

from llama_index.core.workflow import Event
from pydantic import BaseModel, ConfigDict, Field

from droidrun.agent.context import Task


class CodeActExecuteEvent(Event):
    task: Task

class CodeActResultEvent(Event):
    success: bool
    reason: str
    task: Task
    steps: int


class FinalizeEvent(Event):
    success: bool
    # deprecated. use output instead.
    reason: str
    output: str
    # deprecated. use tasks instead.
    task: List[Task]
    tasks: List[Task]
    steps: int = 1

class TaskRunnerEvent(Event):
    pass


class DroidAgentState(BaseModel):
    """
    State model for DroidAgent workflow - shared across parent and child workflows.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    # Task context
    instruction: str = ""
    # App Cards
    app_card: str = ""
    app_card_loading_task: asyncio.Task[str] | None = None
    # Formatted device state for prompts (complete text)
    formatted_device_state: str = ""

    # Focused element text
    focused_text: str = ""

    # Raw device state components (for access to raw data)
    a11y_tree: List[Dict] = Field(default_factory=list)
    phone_state: Dict = Field(default_factory=dict)

    # Derived fields (extracted from phone_state)
    current_package_name: str = ""
    current_app_name: str = ""

    # Previous device state (for before/after comparison in Manager)
    previous_formatted_device_state: str = ""

    # Screen dimensions and screenshot
    width: int = 0
    height: int = 0
    screenshot: str | bytes | None = None

    # Text manipulation flag
    has_text_to_modify: bool = False

    # Action tracking
    action_pool: List[Dict] = Field(default_factory=list)
    action_history: List[Dict] = Field(default_factory=list)
    summary_history: List[str] = Field(default_factory=list)
    action_outcomes: List[bool] = Field(default_factory=list)  # "A", "B", "C"
    error_descriptions: List[str] = Field(default_factory=list)

    # Last action info
    last_action: Dict = Field(default_factory=dict)
    last_summary: str = ""
    last_action_thought: str = ""

    # Memory
    memory: str = ""
    message_history: List[Dict] = Field(default_factory=list)

    # Planning
    plan: str = ""
    current_subgoal: str = ""
    finish_thought: str = ""
    progress_status: str = ""
    manager_answer: str = ""  # For answer-type tasks

    # Error handling
    error_flag_plan: bool = False
    err_to_manager_thresh: int = 2

    # Output
    output_dir: str = ""


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
    For internal events with memory_update metadata, see ManagerInternalPlanEvent.
    """
    plan: str
    current_subgoal: str
    thought: str
    manager_answer: str = ""


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution"""
    current_subgoal: str


class ExecutorResultEvent(Event):
    """
    Coordination event from ExecutorAgent to DroidAgent.

    Used for workflow step routing only (NOT streamed to frontend).
    For internal events with thought/action_json metadata, see ExecutorInternalResultEvent.
    """
    action: Dict
    outcome: bool
    error: str
    summary: str
