import asyncio
import logging
from .actions import Tools
from .device import DeviceManager
from typing import Tuple, Dict, Callable, Any, Optional

# Get a logger for this module
logger = logging.getLogger(__name__)

async def load_tools(serial: Optional[str] = None) -> Tuple[Dict[str, Callable[..., Any]], Tools]:
    """
    Initializes the Tools class and returns a dictionary of available tool functions
    and the Tools instance itself. If serial is not provided, it attempts to find
    the first connected device.

    Args:
        serial: The device serial number. If None, finds the first available device.

    Returns:
        A tuple containing:
        - A dictionary mapping tool names to their corresponding functions.
        - The initialized Tools instance.

    Raises:
        ValueError: If no device serial is provided and no devices are found.
    """
    if serial is None:
        logger.info("No device serial provided, attempting to find a connected device.")
        # Attempt to find a device if none is specified
        device_manager = DeviceManager()
        devices = await device_manager.list_devices()
        if not devices:
            logger.error("Device discovery failed: No connected devices found.")
            raise ValueError("No device serial provided and no connected devices found.")
        serial = devices[0].serial
        logger.info(f"Using auto-detected device: {serial}") # Use logger.info

    logger.debug(f"Initializing Tools for device: {serial}")
    tools_instance = Tools(serial=serial)

    tool_list = {
        # UI interaction
        "swipe": tools_instance.swipe,
        "input_text": tools_instance.input_text,
        "press_key": tools_instance.press_key,
        "tap_by_index": tools_instance.tap_by_index,
        #"tap_by_coordinates": tools_instance.tap_by_coordinates,

        # App management
        "start_app": tools_instance.start_app,
        "list_packages": tools_instance.list_packages,
        "complete": tools_instance.complete
    }
    logger.debug("Base tools loaded.")


    # Return both the dictionary and the instance, as the agent might need the instance
    logger.info(f"Tools loaded successfully for device {serial}.")
    return tool_list, tools_instance