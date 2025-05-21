from typing import List
from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import Event
from llama_index.core.tools import FunctionTool


class InputEvent(Event):
    input: list[ChatMessage]

class ModelResponseEvent(Event):
    response: str


class ExecutePlan(Event):
    pass

class TaskFailedEvent(Event):
    task_description: str
    reason: str

