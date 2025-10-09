from typing import Dict, List

from llama_index.core.workflow import Event
from pydantic import BaseModel, Field

from droidrun.agent.context import Task


class CodeActExecuteEvent(Event):
    task: Task

class CodeActResultEvent(Event):
    success: bool
    reason: str
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



# ============================================================================
# DroidAgentState - State model for llama-index Context
# ============================================================================

class DroidAgentState(BaseModel):
    """
    State model for DroidAgent workflow - shared across parent and child workflows.
    """

    # Task context
    instruction: str = ""

    # UI State
    ui_elements_list_before: str = ""
    ui_elements_list_after: str = ""
    focused_text: str = ""
    device_state_text: str = ""
    width: int = 0
    height: int = 0
    screenshot: str | bytes | None = None
    has_text_to_modify: bool = False

    # Action tracking
    action_pool: List[Dict] = Field(default_factory=list)
    action_history: List[Dict] = Field(default_factory=list)
    summary_history: List[str] = Field(default_factory=list)
    action_outcomes: List[str] = Field(default_factory=list)  # "A", "B", "C"
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
    completed_plan: str = ""
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
    """Manager has created a plan"""
    plan: str
    current_subgoal: str
    completed_plan: str
    thought: str
    manager_answer: str = ""


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution"""
    current_subgoal: str


class ExecutorResultEvent(Event):
    """Executor action result"""
    action: Dict
    outcome: bool
    error: str
    summary: str
