"""
DroidRun - A framework for controlling Android devices through LLM agents.
"""

__version__ = "0.1.0"

# Import main classes for easier access
from .agent.codeact.codeact_agent import CodeActAgent as Agent
from .agent.planner.workflow import PlannerAgent
from .agent.utils.executer import SimpleCodeExecutor
from .agent.utils.llm_picker import load_llm
from .agent.utils.trajectory import (
    save_trajectory,
    load_trajectory,
    get_trajectory_statistics,
    print_trajectory_summary,
    filter_trajectory_steps
)
from .tools.device import DeviceManager
from .tools.actions import Tools
from .tools.loader import load_tools


# Make main components available at package level
__all__ = [
    "Agent",
    "PlannerAgent",
    "DeviceManager",
    "Tools",
    "load_llm",
    "SimpleCodeExecutor",
    "load_tools",
    "save_trajectory",
    "load_trajectory",
    "get_trajectory_statistics",
    "print_trajectory_summary",
    "filter_trajectory_steps"
]