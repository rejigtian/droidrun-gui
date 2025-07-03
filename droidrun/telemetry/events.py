from typing import TypedDict, List
from droidrun.agent.context import Task

class TelemetryEvent(TypedDict):
    pass

class DroidAgentInitEvent(TelemetryEvent):
    goal: str
    llm: str
    tools: str
    personas: str
    max_steps: int
    timeout: int
    vision: bool
    reasoning: bool
    reflection: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: bool


class DroidAgentFinalizeEvent(TelemetryEvent):
    tasks: List[Task]
    reflection: str
    success: bool
    reason: str
    steps: int
