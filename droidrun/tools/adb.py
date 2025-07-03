"""
UI Actions - Core UI interaction tools for Android device control.
"""

import os
import re
import json
import time
import tempfile
import asyncio
import aiofiles
import contextlib
import logging
from typing import Optional, Dict, Tuple, List, Any, Type, Self
from droidrun.adb.device import Device
from droidrun.adb.manager import DeviceManager
from droidrun.tools.tools import Tools

logger = logging.getLogger("droidrun-adb-tools")

class AdbTools(Tools):
    """Core UI interaction tools for Android device control."""

    def __init__(self, serial: str) -> None:
        self.device_manager = DeviceManager()
        # Instance‐level cache for clickable elements (index-based tapping)
        self.clickable_elements_cache: List[Dict[str, Any]] = []
        self.serial = serial
        self.last_screenshot = None
        self.reason = None
        self.success = None
        self.finished = False
        # Memory storage for remembering important information
        self.memory: List[str] = []
        # Store all screenshots with timestamps
        self.screenshots: List[Dict[str, Any]] = []

    @classmethod
    async def create(cls: Type[Self], serial: str = None) -> Self:
        if not serial:
            dvm = DeviceManager()
            devices = await dvm.list_devices()
            if not devices or len(devices) < 1:
                raise ValueError("No devices found")
            serial = devices[0].serial

        return AdbTools(serial)

    def get_device_serial(self) -> str:
        """Get the device serial from the instance or environment variable."""
        # First try using the instance's serial
        if self.serial:
            return self.serial

    async def get_device(self) -> Optional[Device]:
        """Get the device instance using the instance's serial or from environment variable.

        Returns:
            Device instance or None if not found
        """
        serial = self.get_device_serial()
        if not serial:
            raise ValueError("No device serial specified - set device_serial parameter")

        device = await self.device_manager.get_device(serial)
        if not device:
            raise ValueError(f"Device {serial} not found")

        return device

    def parse_package_list(self, output: str) -> List[Dict[str, str]]:
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

    def _parse_content_provider_output(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """
        Parse the raw ADB content provider output and extract JSON data.
        
        Args:
            raw_output (str): Raw output from ADB content query command
            
        Returns:
            dict: Parsed JSON data or None if parsing failed
        """
        # The ADB content query output format is: "Row: 0 result={json_data}"
        # We need to extract the JSON part after "result="
        lines = raw_output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for lines that contain "result=" pattern
            if "result=" in line:
                # Extract everything after "result="
                result_start = line.find("result=") + 7
                json_str = line[result_start:]
                
                try:
                    # Parse the JSON string
                    json_data = json.loads(json_str)
                    return json_data
                except json.JSONDecodeError:
                    continue
            
            # Fallback: try to parse lines that start with { or [
            elif line.startswith('{') or line.startswith('['):
                try:
                    json_data = json.loads(line)
                    return json_data
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found in individual lines, try the entire output
        try:
            json_data = json.loads(raw_output.strip())
            return json_data
        except json.JSONDecodeError:
            return None

    async def tap_by_index(self, index: int, serial: Optional[str] = None) -> str:
        """
        Tap on a UI element by its index.

        This function uses the cached clickable elements
        to find the element with the given index and tap on its center coordinates.

        Args:
            index: Index of the element to tap

        Returns:
            Result message
        """

        def collect_all_indices(elements):
            """Recursively collect all indices from elements and their children."""
            indices = []
            for item in elements:
                if item.get("index") is not None:
                    indices.append(item.get("index"))
                # Check children if present
                children = item.get("children", [])
                indices.extend(collect_all_indices(children))
            return indices

        def find_element_by_index(elements, target_index):
            """Recursively find an element with the given index."""
            for item in elements:
                if item.get("index") == target_index:
                    return item
                # Check children if present
                children = item.get("children", [])
                result = find_element_by_index(children, target_index)
                if result:
                    return result
            return None

        try:
            # Check if we have cached elements
            if not self.clickable_elements_cache:
                return "Error: No UI elements cached. Call get_state first."

            # Find the element with the given index (including in children)
            element = find_element_by_index(self.clickable_elements_cache, index)

            if not element:
                # List available indices to help the user
                indices = sorted(collect_all_indices(self.clickable_elements_cache))
                indices_str = ", ".join(str(idx) for idx in indices[:20])
                if len(indices) > 20:
                    indices_str += f"... and {len(indices) - 20} more"

                return f"Error: No element found with index {index}. Available indices: {indices_str}"

            # Get the bounds of the element
            bounds_str = element.get("bounds")
            if not bounds_str:
                element_text = element.get("text", "No text")
                element_type = element.get("type", "unknown")
                element_class = element.get("className", "Unknown class")
                return f"Error: Element with index {index} ('{element_text}', {element_class}, type: {element_type}) has no bounds and cannot be tapped"

            # Parse the bounds (format: "left,top,right,bottom")
            try:
                left, top, right, bottom = map(int, bounds_str.split(","))
            except ValueError:
                return f"Error: Invalid bounds format for element with index {index}: {bounds_str}"

            # Calculate the center of the element
            x = (left + right) // 2
            y = (top + bottom) // 2

            # Get the device and tap at the coordinates
            if serial:
                device = await self.device_manager.get_device(serial)
                if not device:
                    return f"Error: Device {serial} not found"
            else:
                device = await self.get_device()

            await device.tap(x, y)

            # Add a small delay to allow UI to update
            await asyncio.sleep(0.5)

            # Create a descriptive response
            response_parts = []
            response_parts.append(f"Tapped element with index {index}")
            response_parts.append(f"Text: '{element.get('text', 'No text')}'")
            response_parts.append(f"Class: {element.get('className', 'Unknown class')}")
            response_parts.append(f"Type: {element.get('type', 'unknown')}")

            # Add information about children if present
            children = element.get("children", [])
            if children:
                child_texts = [
                    child.get("text") for child in children if child.get("text")
                ]
                if child_texts:
                    response_parts.append(f"Contains text: {' | '.join(child_texts)}")

            response_parts.append(f"Coordinates: ({x}, {y})")

            return " | ".join(response_parts)
        except ValueError as e:
            return f"Error: {str(e)}"

    # Rename the old tap function to tap_by_coordinates for backward compatibility
    async def tap_by_coordinates(self, x: int, y: int) -> bool:
        """
        Tap on the device screen at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Bool indicating success or failure
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            await device.tap(x, y)
            print(f"Tapped at coordinates ({x}, {y})")
            return True
        except ValueError as e:
            print(f"Error: {str(e)}")
            return False

    # Replace the old tap function with the new one
    async def tap(self, index: int) -> str:
        """
        Tap on a UI element by its index.

        This function uses the cached clickable elements from the last get_clickables call
        to find the element with the given index and tap on its center coordinates.

        Args:
            index: Index of the element to tap

        Returns:
            Result message
        """
        return await self.tap_by_index(index)

    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> bool:
        """
        Performs a straight-line swipe gesture on the device screen.
        To perform a hold (long press), set the start and end coordinates to the same values and increase the duration as needed.
        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration_ms: Duration of swipe in milliseconds
        Returns:
            Bool indicating success or failure
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            await device.swipe(start_x, start_y, end_x, end_y, duration_ms)
            await asyncio.sleep(1)
            print(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration_ms}ms")
            return True
        except ValueError as e:
            print(f"Error: {str(e)}")
            return False

    async def input_text(self, text: str, serial: Optional[str] = None) -> str:
        """
        Input text on the device.
        Always make sure that the Focused Element is not None before inputting text.

        Args:
            text: Text to input. Can contain spaces, newlines, and special characters including non-ASCII.

        Returns:
            Result message
        """
        try:
            if serial:
                device = await self.device_manager.get_device(serial)
                if not device:
                    return f"Error: Device {serial} not found"
            else:
                device = await self.get_device()

            # Save the current keyboard
            original_ime = await device._adb.shell(
                device._serial, "settings get secure default_input_method"
            )
            original_ime = original_ime.strip()

            # Enable the Droidrun keyboard
            await device._adb.shell(
                device._serial, "ime enable com.droidrun.portal/.DroidrunKeyboardIME"
            )

            # Set the Droidrun keyboard as the default
            await device._adb.shell(
                device._serial, "ime set com.droidrun.portal/.DroidrunKeyboardIME"
            )

            # Wait for keyboard to change
            await asyncio.sleep(1)

            # Encode the text to Base64
            import base64

            encoded_text = base64.b64encode(text.encode()).decode()

            cmd = f'content insert --uri "content://com.droidrun.portal/keyboard/input" --bind base64_text:s:"{encoded_text}"'
            await device._adb.shell(device._serial, cmd)

            # Wait for text input to complete
            await asyncio.sleep(0.5)

            # Restore the original keyboard
            if original_ime and "com.droidrun.portal" not in original_ime:
                await device._adb.shell(device._serial, f"ime set {original_ime}")

            return f"Text input completed: {text[:50]}{'...' if len(text) > 50 else ''}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error sending text input: {str(e)}"

    async def back(self) -> str:
        """
        Go back on the current view.
        This presses the Android back button.
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            await device.press_key(3)
            return f"Pressed key BACK"
        except ValueError as e:
            return f"Error: {str(e)}"

    async def press_key(self, keycode: int) -> str:
        """
        Press a key on the Android device.

        Common keycodes:
        - 3: HOME
        - 4: BACK
        - 66: ENTER
        - 67: DELETE

        Args:
            keycode: Android keycode to press
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            key_names = {
                66: "ENTER",
                4: "BACK",
                3: "HOME",
                67: "DELETE",
            }
            key_name = key_names.get(keycode, str(keycode))

            await device.press_key(keycode)
            return f"Pressed key {key_name}"
        except ValueError as e:
            return f"Error: {str(e)}"

    async def start_app(self, package: str, activity: str = "") -> str:
        """
        Start an app on the device.

        Args:
            package: Package name (e.g., "com.android.settings")
            activity: Optional activity name
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            result = await device.start_app(package, activity)
            return result
        except ValueError as e:
            return f"Error: {str(e)}"

    async def install_app(
        self, apk_path: str, reinstall: bool = False, grant_permissions: bool = True
    ) -> str:
        """
        Install an app on the device.

        Args:
            apk_path: Path to the APK file
            reinstall: Whether to reinstall if app exists
            grant_permissions: Whether to grant all permissions
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    return f"Error: Device {self.serial} not found"
            else:
                device = await self.get_device()

            if not os.path.exists(apk_path):
                return f"Error: APK file not found at {apk_path}"

            result = await device.install_app(apk_path, reinstall, grant_permissions)
            return result
        except ValueError as e:
            return f"Error: {str(e)}"

    async def take_screenshot(self) -> Tuple[str, bytes]:
        """
        Take a screenshot of the device.
        This function captures the current screen and adds the screenshot to context in the next message.
        Also stores the screenshot in the screenshots list with timestamp for later GIF creation.
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    raise ValueError(f"Device {self.serial} not found")
            else:
                device = await self.get_device()
            screen_tuple = await device.take_screenshot()
            self.last_screenshot = screen_tuple[1]

            # Store screenshot with timestamp
            self.screenshots.append(
                {
                    "timestamp": time.time(),
                    "image_data": screen_tuple[1],
                    "format": screen_tuple[0],  # Usually 'PNG'
                }
            )
            return screen_tuple
        except ValueError as e:
            raise ValueError(f"Error taking screenshot: {str(e)}")

    async def list_packages(self, include_system_apps: bool = False) -> List[str]:
        """
        List installed packages on the device.

        Args:
            include_system_apps: Whether to include system apps (default: False)

        Returns:
            List of package names
        """
        try:
            if self.serial:
                device = await self.device_manager.get_device(self.serial)
                if not device:
                    raise ValueError(f"Device {self.serial} not found")
            else:
                device = await self.get_device()

            # Use the direct ADB command to get packages with paths
            cmd = ["pm", "list", "packages", "-f"]
            if not include_system_apps:
                cmd.append("-3")

            output = await device._adb.shell(device._serial, " ".join(cmd))

            # Parse the package list using the function
            packages = self.parse_package_list(output)
            # Format package list for better readability
            package_list = [pack["package"] for pack in packages]
            for package in package_list:
                print(package)
            return package_list
        except ValueError as e:
            raise ValueError(f"Error listing packages: {str(e)}")

    async def extract(self, filename: Optional[str] = None) -> str:
        """Extract and save the current UI state to a JSON file.

        This function captures the current UI state including all UI elements
        and saves it to a JSON file for later analysis or reference.

        Args:
            filename: Optional filename to save the UI state (defaults to ui_state_TIMESTAMP.json)

        Returns:
            Path to the saved JSON file
        """
        try:
            # Generate default filename if not provided
            if not filename:
                timestamp = int(time.time())
                filename = f"ui_state_{timestamp}.json"

            # Ensure the filename ends with .json
            if not filename.endswith(".json"):
                filename += ".json"

            # Get the UI elements
            ui_elements = await self.get_all_elements(self.serial)

            # Save to file
            save_path = os.path.abspath(filename)
            async with aiofiles.open(save_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(ui_elements, indent=2))

            return f"UI state extracted and saved to {save_path}"

        except Exception as e:
            return f"Error extracting UI state: {e}"

    async def get_all_elements(self) -> Dict[str, Any]:
        """
        Get all UI elements from the device, including non-interactive elements.

        This function interacts with the TopViewService app installed on the device
        to capture all UI elements, even those that are not interactive. This provides
        a complete view of the UI hierarchy for analysis or debugging purposes.

        Returns:
            Dictionary containing all UI elements extracted from the device screen
        """
        try:
            # Get the device
            device = await self.device_manager.get_device(self.serial)
            if not device:
                raise ValueError(f"Device {self.serial} not found")

            # Create a temporary file for the JSON
            with tempfile.NamedTemporaryFile(suffix=".json") as temp:
                local_path = temp.name

                try:
                    # Clear logcat to make it easier to find our output
                    await device._adb.shell(device._serial, "logcat -c")

                    # Trigger the custom service via broadcast to get ALL elements
                    await device._adb.shell(
                        device._serial,
                        "am broadcast -a com.droidrun.portal.GET_ALL_ELEMENTS",
                    )

                    # Poll for the JSON file path
                    start_time = asyncio.get_event_loop().time()
                    max_wait_time = 10  # Maximum wait time in seconds
                    poll_interval = 0.2  # Check every 200ms

                    device_path = None
                    while asyncio.get_event_loop().time() - start_time < max_wait_time:
                        # Check logcat for the file path
                        logcat_output = await device._adb.shell(
                            device._serial,
                            'logcat -d | grep "DROIDRUN_FILE" | grep "JSON data written to" | tail -1',
                        )

                        # Parse the file path if present
                        match = re.search(r"JSON data written to: (.*)", logcat_output)
                        if match:
                            device_path = match.group(1).strip()
                            break

                        # Wait before polling again
                        await asyncio.sleep(poll_interval)

                    # Check if we found the file path
                    if not device_path:
                        raise ValueError(
                            f"Failed to find the JSON file path in logcat after {max_wait_time} seconds"
                        )

                    logger.debug(f"Pulling file from {device_path} to {local_path}")
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

                        return {
                            "all_elements": ui_data,
                            "count": (
                                len(ui_data)
                                if isinstance(ui_data, list)
                                else sum(1 for _ in ui_data.get("elements", []))
                            ),
                            "message": "Retrieved all UI elements from the device screen",
                        }
                    except json.JSONDecodeError:
                        raise ValueError("Failed to parse UI elements JSON data")

                except Exception as e:
                    # Clean up in case of error
                    with contextlib.suppress(OSError):
                        os.unlink(local_path)
                    raise ValueError(f"Error retrieving all UI elements: {e}")

        except Exception as e:
            raise ValueError(f"Error getting all UI elements: {e}")

    def complete(self, success: bool, reason: str = ""):
        """
        Mark the task as finished.

        Args:
            success: Indicates if the task was successful.
            reason: Reason for failure/success
        """
        if success:
            self.success = True
            self.reason = reason or "Task completed successfully."
            self.finished = True
        else:
            self.success = False
            if not reason:
                raise ValueError("Reason for failure is required if success is False.")
            self.reason = reason
            self.finished = True

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
        if not information or not isinstance(information, str):
            return "Error: Please provide valid information to remember."

        # Add the information to memory
        self.memory.append(information.strip())

        # Limit memory size to prevent context overflow (keep most recent items)
        max_memory_items = 10
        if len(self.memory) > max_memory_items:
            self.memory = self.memory[-max_memory_items:]

        return f"Remembered: {information}"

    def get_memory(self) -> List[str]:
        """
        Retrieve all stored memory items.

        Returns:
            List of stored memory items
        """
        return self.memory.copy()

    async def get_state(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        Get both the a11y tree and phone state in a single call using the combined /state endpoint.

        Args:
            serial: Optional device serial number

        Returns:
            Dictionary containing both 'a11y_tree' and 'phone_state' data
        """
        
        try:
            if serial:
                device = await self.device_manager.get_device(serial)
                if not device:
                    raise ValueError(f"Device {serial} not found")
            else:
                device = await self.get_device()

            adb_output = await device._adb.shell(
                device._serial,
                'content query --uri content://com.droidrun.portal/state'
            )

            state_data = self._parse_content_provider_output(adb_output)
            
            if state_data is None:
                return {
                    "error": "Parse Error",
                    "message": "Failed to parse state data from ContentProvider response"
                }

            if isinstance(state_data, dict) and "data" in state_data:
                data_str = state_data["data"]
                try:
                    combined_data = json.loads(data_str)
                except json.JSONDecodeError:
                    return {
                        "error": "Parse Error",
                        "message": "Failed to parse JSON data from ContentProvider data field"
                    }
            else:
                return {
                    "error": "Format Error",
                    "message": f"Unexpected state data format: {type(state_data)}"
                }

            # Validate that both a11y_tree and phone_state are present
            if "a11y_tree" not in combined_data:
                return {
                    "error": "Missing Data",
                    "message": "a11y_tree not found in combined state data"
                }
            
            if "phone_state" not in combined_data:
                return {
                    "error": "Missing Data", 
                    "message": "phone_state not found in combined state data"
                }

            # Filter out the "type" attribute from all a11y_tree elements
            elements = combined_data["a11y_tree"]
            filtered_elements = []
            for element in elements:
                # Create a copy of the element without the "type" attribute
                filtered_element = {
                    k: v for k, v in element.items() if k != "type"
                }

                # Also filter children if present
                if "children" in filtered_element:
                    filtered_element["children"] = [
                        {k: v for k, v in child.items() if k != "type"}
                        for child in filtered_element["children"]
                    ]

                filtered_elements.append(filtered_element)
            
            self.clickable_elements_cache = filtered_elements
            
            return {
                "a11y_tree": filtered_elements,
                "phone_state": combined_data["phone_state"]
            }

        except Exception as e:
            return {"error": str(e), "message": f"Error getting combined state: {str(e)}"}

if __name__ == "__main__":
    async def main():
        tools = await AdbTools.create()
        print(tools.serial)

    asyncio.run(main())