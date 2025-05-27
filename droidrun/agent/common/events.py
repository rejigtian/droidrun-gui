from llama_index.core.workflow import Event

class ScreenshotEvent(Event):
    screenshot: bytes