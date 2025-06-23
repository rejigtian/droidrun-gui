"""
DroidRun - A framework for controlling Android devices through LLM agents.
"""

__version__ = "0.3.0"

# Import main classes for easier access
from droidrun.agent.codeact.codeact_agent import CodeActAgent
from droidrun.agent.planner.planner_agent import PlannerAgent
from droidrun.agent.utils.executer import SimpleCodeExecutor
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.adb.manager import DeviceManager
from droidrun.tools.tools import Tools
from droidrun.tools.adb import AdbTools
from droidrun.tools.ios import IOSTools
from droidrun.agent.droid import DroidAgent


# Make main components available at package level
__all__ = [
    "DroidAgent",
    "CodeActAgent",
    "PlannerAgent",
    "DeviceManager",
    "Tools",
    "load_llm",
    "SimpleCodeExecutor",
    "Tools",
    "AdbTools",
    "IOSTools",
]
