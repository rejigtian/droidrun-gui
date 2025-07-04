from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from typing import Tuple, Dict, Callable, Any, Optional

# Get a logger for this module
logger = logging.getLogger(__name__)


class Tools(ABC):
    """
    Abstract base class for all tools.
    This class provides a common interface for all tools to implement.
    """

    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the tool.
        """
        pass

    @abstractmethod
    async def tap_by_index(self, index: int) -> bool:
        """
        Tap the element at the given index.
        """
        pass

    #@abstractmethod
    #async def tap_by_coordinates(self, x: int, y: int) -> bool:
    #    pass

    @abstractmethod
    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> bool:
        """
        Swipe from the given start coordinates to the given end coordinates.
        """
        pass

    @abstractmethod
    async def input_text(self, text: str) -> bool:
        """
        Input the given text into a focused input field.
        """
        pass

    @abstractmethod
    async def back(self) -> bool:
        """
        Press the back button.
        """
        pass

    @abstractmethod
    async def press_key(self, keycode: int) -> bool:
        """
        Enter the given keycode.
        """
        pass

    @abstractmethod
    async def start_app(self, package: str, activity: str = "") -> bool:
        """
        Start the given app.
        """
        pass

    @abstractmethod
    async def take_screenshot(self) -> Tuple[str, bytes]:
        """
        Take a screenshot of the device.
        """
        pass

    @abstractmethod
    async def list_packages(self, include_system_apps: bool = False) -> List[str]:
        """
        List all packages on the device.
        """
        pass

    @abstractmethod
    async def remember(self, information: str) -> str:
        """
        Remember the given information. This is used to store information in the tool's memory.
        """
        pass

    @abstractmethod
    async def get_memory(self) -> List[str]:
        """
        Get the memory of the tool.
        """
        pass

    @abstractmethod
    def complete(self, success: bool, reason: str = "") -> bool:
        """
        Complete the tool. This is used to indicate that the tool has completed its task.
        """
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
        # App management
        "start_app": tools.start_app,
        "list_packages": tools.list_packages,
        # state management
        "remember": tools.remember,
        "complete": tools.complete,
    }
