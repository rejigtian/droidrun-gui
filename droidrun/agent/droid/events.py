from llama_index.core.workflow import Event
from droidrun.agent.context import Reflection, Task
from typing import List, Optional

class CodeActExecuteEvent(Event):
    task: Task
    reflection: Optional[Reflection]

class CodeActResultEvent(Event):
    success: bool
    reason: str

class ReasoningLogicEvent(Event):
    pass

class FinalizeEvent(Event):
    success: bool
    reason: str
    task: List[Task]
    steps: int = 1

class TaskRunnerEvent(Event):
    pass

class ReflectionEvent(Event):
    task: Task
    pass