from llama_index.core.workflow import Event
from droidrun.agent.context import Reflection, Task
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

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

class ReflectionEvent(Event):
    task: Task
    pass


# ============================================================================
# DroidAgentState - State model for llama-index Context
# ============================================================================

class DroidAgentState(BaseModel):
    """
    State model for DroidAgent workflow - used with Context[DroidAgentState].

    Context state management:

    - Read state: state = await ctx.store.get_state()
    - Modify state: async with ctx.store.edit_state() as state: ...
    """

    # Task context
    instruction: str = ""
    additional_knowledge_manager: str = ""
    additional_knowledge_executor: str = ""

    # UI State
    ui_elements_list_before: str = ""
    ui_elements_list_after: str = ""
    focused_text: str = ""
    device_state_text: str = ""
    width: int = 0
    height: int = 0

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
    reflection: Optional[Reflection] = None


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
    outcome: str  # "A", "B", "C"
    error: str
    summary: str