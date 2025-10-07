"""
Events for the ManagerAgent workflow.
"""

from llama_index.core.workflow.events import Event


class ManagerThinkingEvent(Event):
    """Manager is thinking about the plan"""
    pass


class ManagerPlanEvent(Event):
    """Manager has created a plan"""
    plan: str
    current_subgoal: str
    completed_plan: str
    thought: str
    manager_answer: str = ""
    memory_update: str = ""
