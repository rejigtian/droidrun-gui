"""
Events for the ExecutorAgent workflow.
"""

from typing import Dict

from llama_index.core.workflow.events import Event


class ExecutorActionEvent(Event):
    """Executor has selected an action to execute"""
    action_json: str
    thought: str
    description: str


class ExecutorResultEvent(Event):
    """Executor action result"""
    action: Dict
    outcome: bool
    error: str
    summary: str
    thought: str = ""
    action_json: str = ""
