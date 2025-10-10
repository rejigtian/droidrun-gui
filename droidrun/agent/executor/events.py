"""
Events for the ExecutorAgent workflow.

These are INTERNAL events used within ExecutorAgent for:
- Streaming to frontend/logging
- Carrying full debug metadata (thought process, raw action JSON)

For workflow coordination with DroidAgent, see droid/events.py
"""

from typing import Dict

from llama_index.core.workflow.events import Event


class ExecutorInternalActionEvent(Event):
    """
    Internal Executor action selection event with thought process.

    This event is streamed to frontend/logging but NOT used for
    workflow coordination between ExecutorAgent and DroidAgent.

    For workflow coordination, see ExecutorInputEvent in droid/events.py
    """
    action_json: str  # Raw JSON string of the action
    thought: str  # Debugging metadata: LLM's reasoning process
    description: str  # Human-readable action description


class ExecutorInternalResultEvent(Event):
    """
    Internal Executor result event with full debug information.

    This event is streamed to frontend/logging but NOT used for
    workflow coordination between ExecutorAgent and DroidAgent.

    For workflow coordination, see ExecutorResultEvent in droid/events.py
    """
    action: Dict
    outcome: bool
    error: str
    summary: str
    thought: str = ""  # Debugging metadata: LLM's thought process
    action_json: str = ""  # Debugging metadata: Raw action JSON
