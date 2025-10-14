"""
Events for ScripterAgent workflow.
"""

from typing import List, Optional

from llama_index.core.workflow import Event


class ScripterInputEvent(Event):
    """Input to LLM (chat history)."""
    input: List  # List of ChatMessages


class ScripterThinkingEvent(Event):
    """LLM generated thought + code."""
    thoughts: str
    code: Optional[str] = None
    full_response: str = ""  # Full LLM response (for fallback when no code)


class ScripterExecutionEvent(Event):
    """Trigger code execution."""
    code: str


class ScripterExecutionResultEvent(Event):
    """Code execution result."""
    output: str


class ScripterEndEvent(Event):
    """Script agent finished."""
    message: str  # Message to Manager
    success: bool  # True if response() called, False if max_steps
    code_executions: int = 0
