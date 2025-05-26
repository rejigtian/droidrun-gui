"""
DroidRun - A framework for controlling Android devices through LLM agents.
"""

__version__ = "0.2.0"

# Import main classes for easier access
from droidrun.agent.codeact.codeact_agent import CodeActAgent
from droidrun.agent.planner.planner_agent import PlannerAgent
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.agent.utils.trajectory import (
    save_trajectory,
    load_trajectory,
    get_trajectory_statistics,
    print_trajectory_summary,
    filter_trajectory_steps
)
from droidrun.adb.manager import DeviceManager
from droidrun.tools.actions import Tools
from droidrun.tools.loader import load_tools


# Make main components available at package level
__all__ = [
    "CodeActAgent",
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