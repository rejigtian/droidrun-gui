from typing import Dict

from pydantic import BaseModel


class TelemetryEvent(BaseModel):
    pass


class DroidAgentInitEvent(TelemetryEvent):
    goal: str
    llms: Dict[str, str]
    tools: str
    max_steps: int
    timeout: int
    vision: Dict[str, bool]
    reasoning: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: str = "none"
    runtype: str = "developer"  # "cli" | "developer" | "web"


class PackageVisitEvent(TelemetryEvent):
    package_name: str
    activity_name: str
    step_number: int


class DroidAgentFinalizeEvent(TelemetryEvent):
    success: bool
    reason: str
    steps: int
    unique_packages_count: int
    unique_activities_count: int
