from typing import Any, Dict

from llama_index.core.workflow import Event


class ScreenshotEvent(Event):
    screenshot: bytes


class RecordUIStateEvent(Event):
    ui_state: list[Dict[str, Any]]
