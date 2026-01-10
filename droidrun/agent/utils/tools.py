"""Tools creation and resolution utilities.

This module provides helpers for creating and resolving Tools instances.
Action functions are in actions.py, signatures in signatures.py.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from droidrun.config_manager.config_manager import DeviceConfig, ToolsConfig
    from droidrun.tools import Tools

from async_adbutils import adb
from droidrun.config_manager.config_manager import ToolsConfig
from droidrun.tools import AdbTools, IOSTools, Tools


async def create_tools_from_config(
    device_config: "DeviceConfig", vision_enabled: bool = True
) -> "Tools":
    """
    Create Tools instance from DeviceConfig.

    Args:
        device_config: Device configuration
        vision_enabled: Whether vision is enabled (for filter selection)

    Returns:
        AdbTools or IOSTools based on config

    Raises:
        ValueError: If no device found or invalid platform
    """
    is_ios = device_config.platform.lower() == "ios"
    device_serial = device_config.serial

    if not is_ios:
        # Android: auto-detect if not specified
        if device_serial is None:
            devices = await adb.list()
            if not devices:
                raise ValueError("No connected Android devices found.")
            device_serial = devices[0].serial
        return AdbTools(serial=device_serial, vision_enabled=vision_enabled)
    else:
        # iOS: require explicit device URL
        if device_serial is None:
            raise ValueError("iOS device URL required in config.device.serial")
        return IOSTools(url=device_serial)


async def resolve_tools_instance(
    tools: "Tools | ToolsConfig | None",
    device_config: "DeviceConfig",
    tools_config_fallback: "ToolsConfig | None" = None,
    credential_manager=None,
    vision_enabled: bool = True,
) -> tuple["Tools", "ToolsConfig"]:
    """
    Resolve Tools instance and ToolsConfig from various input types.

    This helper allows flexible initialization:
    - Pass a Tools instance directly (custom or pre-configured)
    - Pass a ToolsConfig to create Tools from device_config
    - Pass None to use defaults

    Args:
        tools: Either a Tools instance, ToolsConfig, or None
        device_config: Device configuration for creating Tools if needed
        tools_config_fallback: Fallback ToolsConfig when tools is a Tools instance or None
        credential_manager: Optional credential manager to attach to Tools
        vision_enabled: Whether vision is enabled (default: True)

    Returns:
        Tuple of (tools_instance, tools_config):
        - If tools is Tools instance: (tools, tools_config_fallback or default)
        - If tools is ToolsConfig: (created from device_config, tools)
        - If tools is None: (created from device_config, tools_config_fallback or default)

    Example:
        >>> # Use custom Tools instance
        >>> custom_tools = AdbTools(serial="emulator-5554")
        >>> tools_instance, tools_cfg = resolve_tools_instance(custom_tools, device_config)
        >>>
        >>> # Use ToolsConfig (current behavior)
        >>> tools_cfg = ToolsConfig(disabled_tools=["long_press"])
        >>> tools_instance, tools_cfg = resolve_tools_instance(tools_cfg, device_config)
    """
    # Case 1: Tools instance provided directly
    if isinstance(tools, Tools):
        tools_instance = tools
        # Use fallback or default ToolsConfig
        tools_cfg = tools_config_fallback if tools_config_fallback else ToolsConfig()

    # Case 2: ToolsConfig provided
    elif tools is not None and isinstance(tools, ToolsConfig):
        tools_instance = await create_tools_from_config(
            device_config, vision_enabled=vision_enabled
        )
        tools_cfg = tools

    # Case 3: None provided
    else:
        tools_instance = await create_tools_from_config(
            device_config, vision_enabled=vision_enabled
        )
        tools_cfg = tools_config_fallback if tools_config_fallback else ToolsConfig()

    # Attach credential manager if provided
    if credential_manager:
        tools_instance.credential_manager = credential_manager

    return tools_instance, tools_cfg
