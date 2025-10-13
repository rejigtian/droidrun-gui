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


class FinalizeEvent(Event):
    success: bool
    reason: str

class TaskRunnerEvent(Event):
    pass


class DroidAgentState(BaseModel):
    """
    State model for DroidAgent workflow - shared across parent and child workflows.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    # Task context
    instruction: str = ""
    step_number: int = 0
    # App Cards
    app_card: str = ""
    app_card_loading_task: asyncio.Task[str] | None = None
    _app_card_package: str = ""  # Track which package the loading task is for
    _app_card_instruction: str = ""  # Track which instruction the loading task is for
    # Formatted device state for prompts (complete text)
    formatted_device_state: str = ""

    # Focused element text
    focused_text: str = ""

    # Raw device state components (for access to raw data)
    a11y_tree: List[Dict] = Field(default_factory=list)
    phone_state: Dict = Field(default_factory=dict)

    # Private fields
    _current_package_name: str = ""
    _current_activity_name: str = ""
    _visited_packages: set = Field(default_factory=set)
    _visited_activities: set = Field(default_factory=set)

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

    @property
    def current_package_name(self) -> str:
        """Get current package name"""
        return self._current_package_name

    @property
    def current_activity_name(self) -> str:
        """Get current activity name"""
        return self._current_activity_name

    def update_current_app(self, package_name: str, activity_name: str):
        """
        Update package and activity together, capturing telemetry event only once.

        This prevents duplicate PackageVisitEvents when both package and activity change.
        """
        # Check if either changed
        package_changed = package_name != self._current_package_name
        activity_changed = activity_name != self._current_activity_name

        if not (package_changed or activity_changed):
            return  # No change, nothing to do

        # Update tracking sets
        if package_changed and package_name:
            self._visited_packages.add(package_name)
        if activity_changed and activity_name:
            self._visited_activities.add(activity_name)

        # Update values
        self._current_package_name = package_name
        self._current_activity_name = activity_name

        # Capture telemetry event for any change
        # This ensures we track when apps close or transitions to empty state occur
        from droidrun.telemetry import PackageVisitEvent, capture
        capture(
            PackageVisitEvent(
                package_name=package_name or "Unknown",
                activity_name=activity_name or "Unknown",
                step_number=self.step_number,
            )
        )


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
