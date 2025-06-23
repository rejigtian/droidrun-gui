from abc import ABC, abstractmethod
from typing import (
    List,
    Optional,
    Dict,
    Any,
    Tuple,
    Dict,
    Callable,
    Any,
    Optional,
    TypedDict,
)
import logging
import asyncio
from llama_index.core.workflow import Context

# Get a logger for this module
logger = logging.getLogger(__name__)


class Screenshot(TypedDict):
    timestamp: float
    image_data: bytes
    format: str


class Status(TypedDict):
    success: bool
    reason: str
    finished: bool


class Tools(ABC):
    def __init__(self) -> None:
        self.ctx: Context = None

    def set_context(self, ctx: Context) -> None:
        self.ctx = ctx

    def clear_context(self) -> None:
        self.ctx = None

    async def _append_screenshot(self, screenshot: Screenshot) -> None:
        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        # async with self.ctx.lock:
        screenshots = await self.ctx.get("screenshots", [])
        screenshots.append(screenshot)
        await self.ctx.set("screenshots", screenshots)

    async def get_screenshots(self) -> List[Screenshot]:
        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        # async with self.ctx.lock:
        return await self.ctx.get("screenshots", [])

    async def remember(self, information: str) -> str:
        """
        Store important information to remember for future context.

        This information will be extracted and included into your next steps to maintain context
        across interactions. Use this for critical facts, observations, or user preferences
        that should influence future decisions.

        Args:
            information: The information to remember

        Returns:
            Confirmation message
        """
        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        if not information or not isinstance(information, str):
            return "Error: Please provide valid information to remember."

        # async with self.ctx.lock:
        memory = await self.ctx.get("memory", [])

        # Add the information to memory
        memory.append(information.strip())

        # Limit memory size to prevent context overflow (keep most recent items)
        # max_memory_items = 10
        # if len(self.memory) > max_memory_items:
        #    self.memory = self.memory[-max_memory_items:]

        await self.ctx.set("memory", memory)

        return f"Remembered: {information}"

    async def get_memory(self) -> List[str]:
        """
        Retrieve all stored memory items.

        Returns:
            List of stored memory items
        """

        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        # async with self.ctx.lock:
        memory = await self.ctx.get("memory", [])
        return memory.copy()

    async def complete(self, success: bool, reason: str = ""):
        """
        Mark the task as finished.

        Args:
            success: Indicates if the task was successful.
            reason: Reason for failure/success
        """
        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        # async with self.ctx.lock:
        """await asyncio.gather(
            *[
                self.ctx.set("success", success),
                self.ctx.set(
                    "reason",
                    reason
                    or (
                        "Task completed successfully."
                        if success
                        else "Task failed."
                    ),
                ),
                self.ctx.set("finished", True),
            ]
        )"""
        await self.ctx.set(
            "status",
            Status(
                success=success,
                reason=reason
                or ("Task completed successfully." if success else "Task failed."),
                finished=True,
            ),
        )

    async def get_status(self) -> Status:
        if not self.ctx:
            raise RuntimeError("Tools Context is not set")

        # async with self.ctx.lock:
        return await self.ctx.get(
            "status", Status(success=False, reason="", finished=False)
        )

    @abstractmethod
    async def get_clickables(self) -> str:
        pass

    @abstractmethod
    async def tap_by_index(self, index: int) -> bool:
        pass

    # @abstractmethod
    # async def tap_by_coordinates(self, x: int, y: int) -> bool:
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
    async def get_phone_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_packages(self, include_system_apps: bool = False) -> List[str]:
        pass

    @abstractmethod
    async def extract(self, filename: Optional[str] = None) -> str:
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
