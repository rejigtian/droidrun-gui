from llama_index.core.llms import ChatMessage
from llama_index.core.workflow import Event
from typing import Any, Optional

from pydantic import PrivateAttr


class InputEvent(Event):
    input: list[ChatMessage]

class ModelOutputEvent(Event):
    thoughts: Optional[str] = None
    code: Optional[str] = None  

class ExecutionEvent(Event):
    code: str
    globals: dict[str, str] = {}
    locals: dict[str, str] = {}

class ExecutionResultEvent(Event):
    output: str

class FinalizeEvent(Event):
    _result: Any = PrivateAttr(default=None)

    def __init__(self, result: Any = None, **kwargs: Any) -> None:
        # forces the user to provide a result
        super().__init__(_result=result, **kwargs)

    def _get_result(self) -> Any:
        """This can be overridden by subclasses to return the desired result."""
        return self._result

    @property
    def result(self) -> Any:
        return self._get_result()