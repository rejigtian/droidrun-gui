"""
Device - High-level representation of an Android device.
"""

import os
import tempfile
import time
import random
import string
from typing import Dict, Optional, Tuple, List
from droidrun.adb.wrapper import ADBWrapper


class Device:
    """High-level representation of an Android device."""

    def __init__(self, serial: str, adb: ADBWrapper):
        """Initialize device.

        Args:
            serial: Device serial number
            adb: ADB wrapper instance
        """
        self._serial = serial
        self._adb = adb
        self._properties_cache: Dict[str, str] = {}

    @property
    def serial(self) -> str:
        """Get device serial number."""
        return self._serial

    async def get_properties(self) -> Dict[str, str]:
        """Get all device properties."""
        if not self._properties_cache:
            self._properties_cache = await self._adb.get_properties(self._serial)
        return self._properties_cache

    async def get_property(self, name: str) -> str:
        """Get a specific device property."""
        props = await self.get_properties()
        return props.get(name, "")

    @property
    async def model(self) -> str:
        """Get device model."""
        return await self.get_property("ro.product.model")

    @property
    async def brand(self) -> str:
        """Get device brand."""
        return await self.get_property("ro.product.brand")

    @property
    async def android_version(self) -> str:
        """Get Android version."""
        return await self.get_property("ro.build.version.release")

    @property
    async def sdk_level(self) -> str:
        """Get SDK level."""
        return await self.get_property("ro.build.version.sdk")

    async def shell(self, command: str, timeout: float | None = None) -> str:
        """Execute a shell command on the device."""
        return await self._adb.shell(self._serial, command, timeout)

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        await self._adb.shell(self._serial, f"input tap {x} {y}")

    async def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300
    ) -> None:
        """Perform swipe gesture.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration_ms: Swipe duration in milliseconds
        """
        await self._adb.shell(
            self._serial,
            f"input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}",
        )

    async def input_text(self, text: str) -> None:
        """Input text.

        Args:
            text: Text to input
        """
        await self._adb.shell(self._serial, f"input text {text}")

    async def press_key(self, keycode: int) -> None:
        """Press a key.

        Args:
            keycode: Android keycode to press
        """
        await self._adb.shell(self._serial, f"input keyevent {keycode}")

    async def start_activity(
        self,
        package: str,
        activity: str = ".MainActivity",
        extras: Optional[Dict[str, str]] = None,
    ) -> None:
        """Start an app activity.

        Args:
            package: Package name
            activity: Activity name
            extras: Intent extras
        """
        cmd = f"am start -n {package}/{activity}"
        if extras:
            for key, value in extras.items():
                cmd += f" -e {key} {value}"
        await self._adb.shell(self._serial, cmd)

    async def start_app(self, package: str, activity: str = "") -> str:
        """Start an app on the device.

        Args:
            package: Package name
            activity: Optional activity name (if empty, launches default activity)

        Returns:
            Result message
        """
        if activity:
            if not activity.startswith(".") and "." not in activity:
                activity = f".{activity}"

            if (
                not activity.startswith(".")
                and "." in activity
                and not activity.startswith(package)
            ):
                # Fully qualified activity name
                component = activity.split("/", 1)
                return await self.start_activity(
                    component[0], component[1] if len(component) > 1 else activity
                )

            # Relative activity name
            return await self.start_activity(package, activity)

        # Start main activity using monkey
        cmd = f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        result = await self._adb.shell(self._serial, cmd)
        return f"Started {package}"

    async def install_app(
        self, apk_path: str, reinstall: bool = False, grant_permissions: bool = True
    ) -> str:
        """Install an APK on the device.

        Args:
            apk_path: Path to the APK file
            reinstall: Whether to reinstall if app exists
            grant_permissions: Whether to grant all requested permissions

        Returns:
            Installation result
        """
        if not os.path.exists(apk_path):
            return f"Error: APK file not found: {apk_path}"

        # Build install command args
        install_args = ["install"]
        if reinstall:
            install_args.append("-r")
        if grant_permissions:
            install_args.append("-g")
        install_args.append(apk_path)

        try:
            stdout, stderr = await self._adb._run_device_command(
                self._serial,
                install_args,
                timeout=120,  # Longer timeout for installation
            )

            if "success" in stdout.lower():
                return f"Successfully installed {os.path.basename(apk_path)}"
            return f"Installation failed: {stdout or stderr}"

        except Exception as e:
            return f"Installation failed: {str(e)}"

    async def uninstall_app(self, package: str, keep_data: bool = False) -> str:
        """Uninstall an app from the device.

        Args:
            package: Package name to uninstall
            keep_data: Whether to keep app data and cache directories

        Returns:
            Uninstallation result
        """
        cmd = ["pm", "uninstall"]
        if keep_data:
            cmd.append("-k")
        cmd.append(package)

        result = await self._adb.shell(self._serial, " ".join(cmd))
        return result.strip()

    async def take_screenshot(self, quality: int = 75) -> Tuple[str, bytes]:
        """Take a screenshot of the device and compress it.

        Args:
            quality: JPEG quality (1-100, lower means smaller file size)

        Returns:
            Tuple of (local file path, screenshot data as bytes)
        """
        # Create a temporary file for the screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            screenshot_path = temp.name

        try:
            # Generate a random filename for the device
            timestamp = int(time.time())
            random_suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=8)
            )
            device_path = f"/sdcard/screenshot_{timestamp}_{random_suffix}.png"

            # Take screenshot using screencap command
            await self._adb.shell(self._serial, f"screencap -p {device_path}")

            # Pull screenshot to local machine
            await self._adb._run_device_command(
                self._serial, ["pull", device_path, screenshot_path]
            )

            # Clean up on device
            await self._adb.shell(self._serial, f"rm {device_path}")

            # Read the screenshot file
            with open(screenshot_path, "rb") as f:
                screenshot_data = f.read()

            # Convert and compress the image
            try:
                from PIL import Image
                import io

                # Create buffer for the compressed image
                buffer = io.BytesIO()

                # Load the PNG data into a PIL Image
                with Image.open(io.BytesIO(screenshot_data)) as img:
                    # Convert to RGB (removing alpha channel if present) and save as JPEG
                    converted_img = img.convert("RGB") if img.mode == "RGBA" else img
                    converted_img.save(
                        buffer, format="JPEG", quality=quality, optimize=True
                    )
                    compressed_data = buffer.getvalue()

                # Get size reduction info for logging
                png_size = len(screenshot_data) / 1024
                jpg_size = len(compressed_data) / 1024
                reduction = 100 - (jpg_size / png_size * 100) if png_size > 0 else 0

                import logging

                logger = logging.getLogger("droidrun")
                logger.debug(
                    f"Screenshot compressed successfully: {png_size:.1f}KB → {jpg_size:.1f}KB ({reduction:.1f}% reduction)"
                )

                return screenshot_path, compressed_data
            except ImportError:
                # If PIL is not available, return the original PNG data
                logger.warning("PIL not available, returning uncompressed screenshot")
                return screenshot_path, screenshot_data
            except Exception as e:
                # If compression fails, return the original PNG data
                logger.warning(
                    f"Screenshot compression failed: {e}, returning uncompressed"
                )
                return screenshot_path, screenshot_data

        except Exception as e:
            # Clean up in case of error
            try:
                os.unlink(screenshot_path)
            except OSError:
                pass
            raise RuntimeError(f"Screenshot capture failed: {str(e)}")

    async def list_packages(
        self, include_system_apps: bool = False
    ) -> List[Dict[str, str]]:
        """List installed packages on the device.

        Args:
            include_system_apps: Whether to include system apps

        Returns:
            List of package dictionaries with 'package' and 'path' keys
        """
        cmd = ["pm", "list", "packages", "-f"]
        if not include_system_apps:
            cmd.append("-3")

        output = await self._adb.shell(self._serial, " ".join(cmd))

        packages = []
        for line in output.splitlines():
            if line.startswith("package:"):
                parts = line[8:].split("=")
                if len(parts) == 2:
                    path, package = parts
                    packages.append({"package": package, "path": path})

        return packages
