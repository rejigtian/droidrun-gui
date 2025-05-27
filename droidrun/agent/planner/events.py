from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import Event
from llama_index.core.workflow import Event
from typing import Optional, Any


class InputEvent(Event):
    input: list[ChatMessage]

class ModelResponseEvent(Event):
    thoughts: Optional[str] = None
    code: Optional[str] = None  


class ExecutePlan(Event):
    pass

class TaskFailedEvent(Event):
    task_description: str
    reason: str

class FinalizeEvent(Event):
    pass

class PlannerCodeExecutionEvent(Event):
    result: Any

