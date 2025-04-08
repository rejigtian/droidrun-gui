"""
UI Actions - Core UI interaction tools for Android device control.
"""

import os
import re
import tempfile
import asyncio
import aiofiles
import contextlib
from typing import Optional, Dict, Tuple, List, Any
from droidrun.adb import Device, DeviceManager

# Global variable to store clickable elements for index-based tapping
CLICKABLE_ELEMENTS_CACHE = []

# Default device serial will be read from environment variable
def get_device_serial() -> str:
    """Get the device serial from environment variable.
    
    Returns:
        Device serial from environment or None
    """
    return os.environ.get("DROIDRUN_DEVICE_SERIAL", "")

async def get_device() -> Optional[Device]:
    """Get the device instance using the serial from environment variable.
    
    Returns:
        Device instance or None if not found
    """
    serial = get_device_serial()
    if not serial:
        raise ValueError("DROIDRUN_DEVICE_SERIAL environment variable not set")
        
    device_manager = DeviceManager()
    device = await device_manager.get_device(serial)
    if not device:
        raise ValueError(f"Device {serial} not found")
    
    return device

def parse_package_list(output: str) -> List[Dict[str, str]]:
    """Parse the output of 'pm list packages -f' command.

    Args:
        output: Raw command output from 'pm list packages -f'

    Returns:
        List of dictionaries containing package info with 'package' and 'path' keys
    """
    apps = []
    for line in output.splitlines():
        if line.startswith("package:"):
            # Format is: "package:/path/to/base.apk=com.package.name"
            path_and_pkg = line[8:]  # Strip "package:"
            if "=" in path_and_pkg:
                path, package = path_and_pkg.rsplit("=", 1)
                apps.append({"package": package.strip(), "path": path.strip()})
    return apps

async def get_ui_elements(serial: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all UI elements from the device using the custom TopViewService.
    
    This function interacts with the TopViewService app installed on the device
    to capture the current UI hierarchy and elements. The service writes UI data
    to a JSON file on the device, which is then pulled to the host.
    
    Args:
        serial: Optional device serial number
    
    Returns:
        Dictionary containing UI elements extracted from the device screen
    """
    try:
        # Get the device
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                raise ValueError(f"Device {serial} not found")
        else:
            device = await get_device()
        
        # Create a temporary file for the JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
            local_path = temp.name
        
        try:
            # Clear logcat to make it easier to find our output
            await device._adb.shell(device._serial, "logcat -c")
            
            # Trigger the custom service via broadcast
            await device._adb.shell(device._serial, "am broadcast -a com.example.droidrun.GET_ELEMENTS")
            
            # Poll for the JSON file path
            start_time = asyncio.get_event_loop().time()
            max_wait_time = 10  # Maximum wait time in seconds
            poll_interval = 0.2  # Check every 200ms
            
            device_path = None
            while asyncio.get_event_loop().time() - start_time < max_wait_time:
                # Check logcat for the file path
                logcat_output = await device._adb.shell(device._serial, "logcat -d | grep \"DROIDRUN_FILE\" | grep \"JSON data written to\" | tail -1")
                
                # Parse the file path if present
                match = re.search(r"JSON data written to: (.*)", logcat_output)
                if match:
                    device_path = match.group(1).strip()
                    break
                    
                # Wait before polling again
                await asyncio.sleep(poll_interval)
            
            # Check if we found the file path
            if not device_path:
                raise ValueError(f"Failed to find the JSON file path in logcat after {max_wait_time} seconds")
                
            # Pull the JSON file from the device
            await device._adb.pull_file(device._serial, device_path, local_path)
            
            # Read the JSON file
            async with aiofiles.open(local_path, "r", encoding="utf-8") as f:
                json_content = await f.read()
            
            # Clean up the temporary file
            with contextlib.suppress(OSError):
                os.unlink(local_path)
            
            # Try to parse the JSON
            import json
            try:
                ui_data = json.loads(json_content)
                return ui_data
            except json.JSONDecodeError:
                raise ValueError("Failed to parse UI elements JSON data")
            
        except Exception as e:
            # Clean up in case of error
            with contextlib.suppress(OSError):
                os.unlink(local_path)
            raise ValueError(f"Error retrieving UI elements: {e}")
            
    except Exception as e:
        raise ValueError(f"Error getting UI elements: {e}")

async def get_clickables(serial: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all clickable UI elements from the device using the custom TopViewService.
    
    This function interacts with the TopViewService app installed on the device
    to capture only the clickable UI elements. The service writes UI data
    to a JSON file on the device, which is then pulled to the host.
    
    Args:
        serial: Optional device serial number
    
    Returns:
        Dictionary containing clickable UI elements extracted from the device screen
    """
    global CLICKABLE_ELEMENTS_CACHE
    
    try:
        # Get the device
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                raise ValueError(f"Device {serial} not found")
        else:
            device = await get_device()
        
        # Create a temporary file for the JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
            local_path = temp.name
        
        try:
            # Clear logcat to make it easier to find our output
            await device._adb.shell(device._serial, "logcat -c")
            
            # Trigger the custom service via broadcast to get only interactive elements
            await device._adb.shell(device._serial, "am broadcast -a com.example.droidrun.GET_ELEMENTS")
            
            # Poll for the JSON file path
            start_time = asyncio.get_event_loop().time()
            max_wait_time = 10  # Maximum wait time in seconds
            poll_interval = 0.2  # Check every 200ms
            
            device_path = None
            while asyncio.get_event_loop().time() - start_time < max_wait_time:
                # Check logcat for the file path
                logcat_output = await device._adb.shell(device._serial, "logcat -d | grep \"DROIDRUN_FILE\" | grep \"JSON data written to\" | tail -1")
                
                # Parse the file path if present
                match = re.search(r"JSON data written to: (.*)", logcat_output)
                if match:
                    device_path = match.group(1).strip()
                    break
                    
                # Wait before polling again
                await asyncio.sleep(poll_interval)
            
            # Check if we found the file path
            if not device_path:
                raise ValueError(f"Failed to find the JSON file path in logcat after {max_wait_time} seconds")
                
            # Pull the JSON file from the device
            await device._adb.pull_file(device._serial, device_path, local_path)
            
            # Read the JSON file
            async with aiofiles.open(local_path, "r", encoding="utf-8") as f:
                json_content = await f.read()
                
            # Add logging of raw JSON content
            print("Raw JSON response from device:")
            print(json_content)
            
            # Clean up the temporary file
            with contextlib.suppress(OSError):
                os.unlink(local_path)
            
            # Try to parse the JSON
            import json
            try:
                ui_data = json.loads(json_content)
                
                # Add logging of parsed data
                print("\nParsed JSON data:")
                print(json.dumps(ui_data, indent=2))
                
                # Handle both possible response formats
                if isinstance(ui_data, list):
                    # If the response is a list, it's already the clickable elements
                    clickable_elements = ui_data
                else:
                    # If it's a dictionary, extract the clickable_elements field
                    clickable_elements = ui_data.get("clickable_elements", [])

                # Update the global cache with the new elements
                CLICKABLE_ELEMENTS_CACHE = clickable_elements
                
                return {
                    "clickable_elements": clickable_elements,
                    "count": len(clickable_elements),
                    "message": f"Found {len(clickable_elements)} clickable elements on screen"
                }
            except json.JSONDecodeError:
                raise ValueError("Failed to parse UI elements JSON data")
            
        except Exception as e:
            # Clean up in case of error
            with contextlib.suppress(OSError):
                os.unlink(local_path)
            raise ValueError(f"Error retrieving clickable elements: {e}")
            
    except Exception as e:
        raise ValueError(f"Error getting clickable elements: {e}")

async def tap_by_index(index: int, serial: Optional[str] = None) -> str:
    """
    Tap on a UI element by its index.
    
    This function uses the cached clickable elements from the last get_clickables call
    to find the element with the given index and tap on its center coordinates.
    
    Args:
        index: Index of the element to tap
        serial: Optional device serial (for backward compatibility)
    
    Returns:
        Result message
    """
    global CLICKABLE_ELEMENTS_CACHE
    
    try:
        # Check if we have cached elements
        if not CLICKABLE_ELEMENTS_CACHE:
            return "Error: No UI elements cached. Call get_clickables first."
        
        # Find the element with the given index
        element = None
        for item in CLICKABLE_ELEMENTS_CACHE:
            if item.get('index') == index:
                element = item
                break
        
        if not element:
            return f"Error: No element found with index {index}"
        
        # Get the bounds of the element
        bounds_str = element.get('bounds')
        if not bounds_str:
            return f"Error: Element with index {index} has no bounds"
        
        # Parse the bounds (format: "left,top,right,bottom")
        try:
            left, top, right, bottom = map(int, bounds_str.split(','))
        except ValueError:
            return f"Error: Invalid bounds format for element with index {index}: {bounds_str}"
        
        # Calculate the center of the element
        x = (left + right) // 2
        y = (top + bottom) // 2
        
        # Get the device and tap at the coordinates
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        await device.tap(x, y)
        
        element_text = element.get('text', 'No text')
        element_class = element.get('className', 'Unknown class')
        
        return f"Tapped element with index {index} ({element_text}, {element_class}) at ({x}, {y})"
    except ValueError as e:
        return f"Error: {str(e)}"

# Rename the old tap function to tap_by_coordinates for backward compatibility
async def tap_by_coordinates(x: int, y: int, serial: Optional[str] = None) -> str:
    """
    Tap on the device screen at specific coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        await device.tap(x, y)
        return f"Tapped at ({x}, {y})"
    except ValueError as e:
        return f"Error: {str(e)}"

# Replace the old tap function with the new one
async def tap(index: int, serial: Optional[str] = None) -> str:
    """
    Tap on a UI element by its index.
    
    This function uses the cached clickable elements from the last get_clickables call
    to find the element with the given index and tap on its center coordinates.
    
    Args:
        index: Index of the element to tap
        serial: Optional device serial (for backward compatibility)
    
    Returns:
        Result message
    """
    return await tap_by_index(index, serial)

async def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 300,
    serial: Optional[str] = None
) -> str:
    """
    Perform a swipe gesture on the device screen.
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration_ms: Duration of swipe in milliseconds
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        await device.swipe(start_x, start_y, end_x, end_y, duration_ms)
        return f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})"
    except ValueError as e:
        return f"Error: {str(e)}"

async def input_text(text: str, serial: Optional[str] = None) -> str:
    """
    Input text on the device.
    
    Args:
        text: Text to input. Can contain spaces and special characters.
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        # Ensure text is properly escaped for shell command
        escaped_text = text.replace('"', '\\"')  # Escape double quotes
        await device._adb.shell(device._serial, f'input text "{escaped_text}"')
        return f"Text input completed: {text}"
    except ValueError as e:
        return f"Error: {str(e)}"

async def press_key(keycode: int, serial: Optional[str] = None) -> str:
    """
    Press a key on the device.
    
    Common keycodes:
    - 3: HOME
    - 4: BACK
    - 24: VOLUME UP
    - 25: VOLUME DOWN
    - 26: POWER
    - 82: MENU
    
    Args:
        keycode: Android keycode to press
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        key_names = {
            3: "HOME",
            4: "BACK",
            24: "VOLUME UP",
            25: "VOLUME DOWN",
            26: "POWER",
            82: "MENU",
        }
        key_name = key_names.get(keycode, str(keycode))
        
        await device.press_key(keycode)
        return f"Pressed key {key_name}"
    except ValueError as e:
        return f"Error: {str(e)}"

async def start_app(
    package: str,
    activity: str = "",
    serial: Optional[str] = None
) -> str:
    """
    Start an app on the device.
    
    Args:
        package: Package name (e.g., "com.android.settings")
        activity: Optional activity name
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        result = await device.start_app(package, activity)
        return result
    except ValueError as e:
        return f"Error: {str(e)}"

async def install_app(
    apk_path: str, 
    reinstall: bool = False, 
    grant_permissions: bool = True,
    serial: Optional[str] = None
) -> str:
    """
    Install an app on the device.
    
    Args:
        apk_path: Path to the APK file
        reinstall: Whether to reinstall if app exists
        grant_permissions: Whether to grant all permissions
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        if not os.path.exists(apk_path):
            return f"Error: APK file not found at {apk_path}"
        
        result = await device.install_app(apk_path, reinstall, grant_permissions)
        return result
    except ValueError as e:
        return f"Error: {str(e)}"

async def uninstall_app(
    package: str, 
    keep_data: bool = False,
    serial: Optional[str] = None
) -> str:
    """
    Uninstall an app from the device.
    
    Args:
        package: Package name to uninstall
        keep_data: Whether to keep app data and cache
        serial: Optional device serial (for backward compatibility)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                return f"Error: Device {serial} not found"
        else:
            device = await get_device()
        
        result = await device.uninstall_app(package, keep_data)
        return result
    except ValueError as e:
        return f"Error: {str(e)}"

async def take_screenshot(serial: Optional[str] = None) -> Tuple[str, bytes]:
    """
    Take a screenshot of the device.
    
    Args:
        serial: Optional device serial (for backward compatibility)
    
    Returns:
        Tuple of (local file path, screenshot data as bytes)
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                raise ValueError(f"Device {serial} not found")
        else:
            device = await get_device()
        
        return await device.take_screenshot()
    except ValueError as e:
        raise ValueError(f"Error taking screenshot: {str(e)}")

async def list_packages(
    include_system_apps: bool = False,
    serial: Optional[str] = None
) -> Dict[str, Any]:
    """
    List installed packages on the device.
    
    Args:
        include_system_apps: Whether to include system apps (default: False)
        serial: Optional device serial (for backward compatibility)
    
    Returns:
        Dictionary containing:
        - packages: List of dictionaries with 'package' and 'path' keys
        - count: Number of packages found
        - type: Type of packages listed ("all" or "non-system")
    """
    try:
        if serial:
            device_manager = DeviceManager()
            device = await device_manager.get_device(serial)
            if not device:
                raise ValueError(f"Device {serial} not found")
        else:
            device = await get_device()
        
        # Use the direct ADB command to get packages with paths
        cmd = ["pm", "list", "packages", "-f"]
        if not include_system_apps:
            cmd.append("-3")
            
        output = await device._adb.shell(device._serial, " ".join(cmd))
        
        # Parse the package list using the function
        packages = parse_package_list(output)
        package_type = "all" if include_system_apps else "non-system"
        
        return {
            "packages": packages,
            "count": len(packages),
            "type": package_type,
            "message": f"Found {len(packages)} {package_type} packages on the device"
        }
    except ValueError as e:
        raise ValueError(f"Error listing packages: {str(e)}")

async def complete(result: str) -> str:
    """
    Signal that the agent has completed its goal and provide the final result.
    
    IMPORTANT: This function does NOT perform any actions itself. It should ONLY be called
    after you have ACTUALLY completed all necessary actions for the goal through other tools.
    This is simply a way to signal completion and provide a summary of what was already accomplished.
    
    Incorrect usage:
    - Calling this function to try to complete the task
    - Calling this function before all necessary actions are done
    - Using this as the last action without having achieved the goal
    
    Correct usage:
    - Call this function only after you have successfully completed all required actions
    - Include a detailed summary of what was actually accomplished
    
    Args:
        result: A summary of what was accomplished or the final result
        
    Returns:
        Success message with the result
    """
    return f"Goal completed successfully. Result: {result}"