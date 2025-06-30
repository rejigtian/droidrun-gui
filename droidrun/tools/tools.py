from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from typing import Tuple, Dict, Callable, Any, Optional

# Get a logger for this module
logger = logging.getLogger(__name__)


class Tools(ABC):
    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def tap_by_index(self, index: int) -> bool:
        pass

    #@abstractmethod
    #async def tap_by_coordinates(self, x: int, y: int) -> bool:
    #    pass

    @abstractmethod
    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> bool:
        pass

    @abstractmethod
    async def input_text(self, text: str) -> bool:
        pass

    @abstractmethod
    async def back(self) -> bool:
        pass

    @abstractmethod
    async def press_key(self, keycode: int) -> bool:
        pass

    @abstractmethod
    async def start_app(self, package: str, activity: str = "") -> bool:
        pass

    @abstractmethod
    async def take_screenshot(self) -> Tuple[str, bytes]:
        pass

    @abstractmethod
    async def list_packages(self, include_system_apps: bool = False) -> List[str]:
        pass

    @abstractmethod
    async def remember(self, information: str) -> str:
        pass

    @abstractmethod
    async def get_memory(self) -> List[str]:
        pass

    @abstractmethod
    async def extract(self, filename: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def complete(self, success: bool, reason: str = "") -> bool:
        pass


def describe_tools(tools: Tools) -> Dict[str, Callable[..., Any]]:
    """
    Describe the tools available for the given Tools instance.

    Args:
        tools: The Tools instance to describe.

    Returns:
        A dictionary mapping tool names to their descriptions.
    """

    return {
        # UI interaction
        "swipe": tools.swipe,
        "input_text": tools.input_text,
        "press_key": tools.press_key,
        "tap_by_index": tools.tap_by_index,
        # "tap_by_coordinates": tools_instance.tap_by_coordinates,
        # App management
        "start_app": tools.start_app,
        "list_packages": tools.list_packages,
        # state management
        "extract": tools.extract,
        "remember": tools.remember,
        "complete": tools.complete,
    }
