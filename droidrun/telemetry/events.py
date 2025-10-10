from typing import Dict

from pydantic import BaseModel


class TelemetryEvent(BaseModel):
    pass

class DroidAgentInitEvent(TelemetryEvent):
    goal: str
    llms: str | Dict[str, str]
    tools: str
    max_steps: int
    timeout: int
    vision: bool | Dict[str, bool]
    reasoning: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: str = "none",


class DroidAgentFinalizeEvent(TelemetryEvent):
    tasks: str
    success: bool
    output: str
    steps: int
