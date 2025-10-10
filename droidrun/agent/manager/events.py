"""
Events for the ManagerAgent workflow.

These are INTERNAL events used within ManagerAgent for:
- Streaming to frontend/logging
- Carrying full debug metadata

For workflow coordination with DroidAgent, see droid/events.py
"""

from llama_index.core.workflow.events import Event


class ManagerThinkingEvent(Event):
    """Manager is thinking about the plan"""
    pass


class ManagerInternalPlanEvent(Event):
    """
    Internal Manager planning event with full state and metadata.

    This event is streamed to frontend/logging but NOT used for
    workflow coordination between ManagerAgent and DroidAgent.

    For workflow coordination, see ManagerPlanEvent in droid/events.py
    """
    plan: str
    current_subgoal: str
    thought: str
    manager_answer: str = ""
    memory_update: str = ""  # Debugging metadata: LLM's memory additions
