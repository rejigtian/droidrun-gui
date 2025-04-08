"""
ADB Wrapper - Lightweight wrapper around ADB for Android device control.
"""

import asyncio
import os
import shlex
from typing import Dict, List, Optional, Tuple

class ADBWrapper:
    """Lightweight wrapper around ADB for Android device control."""

    def __init__(self, adb_path: Optional[str] = None):
        """Initialize ADB wrapper.
        
        Args:
            adb_path: Path to ADB binary (defaults to 'adb' in PATH)
        """
        self.adb_path = adb_path or "adb"
        self._devices_cache: List[Dict[str, str]] = []

    async def _run_command(
        self, 
        args: List[str], 
        timeout: Optional[float] = None,
        check: bool = True
    ) -> Tuple[str, str]:
        """Run an ADB command.
        
        Args:
            args: Command arguments
            timeout: Command timeout in seconds
            check: Whether to check return code
            
        Returns:
            Tuple of (stdout, stderr)
        """
        cmd = [self.adb_path, *args]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if timeout is not None:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout
                )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()

            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

            if check and process.returncode != 0:
                raise RuntimeError(f"ADB command failed: {stderr or stdout}")

            return stdout, stderr

        except asyncio.TimeoutError:
            raise TimeoutError(f"ADB command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise FileNotFoundError(f"ADB not found at {self.adb_path}")

    async def _run_device_command(
        self, 
        serial: str, 
        args: List[str], 
        timeout: Optional[float] = None,
        check: bool = True
    ) -> Tuple[str, str]:
        """Run an ADB command for a specific device."""
        return await self._run_command(["-s", serial, *args], timeout, check)

    async def get_devices(self) -> List[Dict[str, str]]:
        """Get list of connected devices.
        
        Returns:
            List of device info dictionaries with 'serial' and 'status' keys
        """
        stdout, _ = await self._run_command(["devices", "-l"])
        
        devices = []
        for line in stdout.splitlines()[1:]:  # Skip first line (header)
            if not line.strip():
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            serial = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            
            devices.append({
                "serial": serial,
                "status": status
            })
            
        self._devices_cache = devices
        return devices

    async def connect(self, host: str, port: int = 5555) -> str:
        """Connect to a device over TCP/IP.
        
        Args:
            host: Device IP address
            port: Device port
            
        Returns:
            Device serial number (host:port)
        """
        serial = f"{host}:{port}"
        
        # Check if already connected
        devices = await self.get_devices()
        if any(d["serial"] == serial for d in devices):
            return serial
            
        stdout, _ = await self._run_command(["connect", serial], timeout=10.0)
        
        if "connected" not in stdout.lower():
            raise RuntimeError(f"Failed to connect: {stdout}")
            
        return serial

    async def disconnect(self, serial: str) -> bool:
        """Disconnect from a device.
        
        Args:
            serial: Device serial number
            
        Returns:
            True if disconnected successfully
        """
        try:
            stdout, _ = await self._run_command(["disconnect", serial])
            return "disconnected" in stdout.lower()
        except Exception:
            return False

    async def shell(self, serial: str, command: str, timeout: Optional[float] = None) -> str:
        """Run a shell command on the device.
        
        Args:
            serial: Device serial number
            command: Shell command to run
            timeout: Command timeout in seconds
            
        Returns:
            Command output
        """
        stdout, _ = await self._run_device_command(serial, ["shell", command], timeout=timeout)
        return stdout

    async def get_properties(self, serial: str) -> Dict[str, str]:
        """Get device properties.
        
        Args:
            serial: Device serial number
            
        Returns:
            Dictionary of device properties
        """
        output = await self.shell(serial, "getprop")
        
        properties = {}
        for line in output.splitlines():
            if not line or "[" not in line or "]" not in line:
                continue
                
            try:
                key = line.split("[")[1].split("]")[0]
                value = line.split("[")[2].split("]")[0]
                properties[key] = value
            except IndexError:
                continue
                
        return properties
        
    async def install_app(
        self, 
        serial: str, 
        apk_path: str, 
        reinstall: bool = False, 
        grant_permissions: bool = True
    ) -> Tuple[str, str]:
        """Install an APK on the device.
        
        Args:
            serial: Device serial number
            apk_path: Path to the APK file
            reinstall: Whether to reinstall if app exists
            grant_permissions: Whether to grant all permissions
            
        Returns:
            Tuple of (stdout, stderr)
        """
        args = ["install"]
        if reinstall:
            args.append("-r")
        if grant_permissions:
            args.append("-g")
        args.append(apk_path)
        
        return await self._run_device_command(serial, args, timeout=120.0)
        
    async def pull_file(self, serial: str, device_path: str, local_path: str) -> Tuple[str, str]:
        """Pull a file from the device.
        
        Args:
            serial: Device serial number
            device_path: Path on the device
            local_path: Path on the local machine
            
        Returns:
            Tuple of (stdout, stderr)
        """
        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir)
            
        return await self._run_device_command(serial, ["pull", device_path, local_path], timeout=60.0) 