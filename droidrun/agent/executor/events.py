"""
Events for the ExecutorAgent workflow.
"""

from llama_index.core.workflow.events import Event
from typing import Dict


class ExecutorThinkingEvent(Event):
    """Executor is thinking about which action to take"""
    subgoal: str


class ExecutorActionEvent(Event):
    """Executor has selected an action to execute"""
    action_json: str
    thought: str
    description: str


class ExecutorResultEvent(Event):
    """Executor action result"""
    action: Dict
    outcome: str  # "A" = success, "B" = partial, "C" = failure
    error: str
    summary: str
    thought: str = ""
    action_json: str = ""
