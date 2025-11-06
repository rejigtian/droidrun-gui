"""
DroidRun - A framework for controlling Android devices through LLM agents.
"""

__version__ = "0.4.4dev"

# Import main classes for easier access
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm

# Import macro functionality
from droidrun.macro import MacroPlayer, replay_macro_file, replay_macro_folder
from droidrun.tools import AdbTools, IOSTools, Tools
from droidrun.agent import ResultEvent
from droidrun.config_manager import DroidrunConfig, DeviceConfig

# Make main components available at package level
__all__ = [
    "DroidAgent",
    "load_llm",
    "Tools",
    "AdbTools",
    "IOSTools",
    "MacroPlayer",
    "replay_macro_file",
    "replay_macro_folder",
    "ResultEvent",
    "DroidrunConfig",
    "DeviceConfig",
]
