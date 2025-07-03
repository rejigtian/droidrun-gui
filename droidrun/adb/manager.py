"""
Device Manager - Manages Android device connections.
"""

from typing import Dict, List, Optional
from droidrun.adb.wrapper import ADBWrapper
from droidrun.adb.device import Device

class DeviceManager:
    """Manages Android device connections."""

    def __init__(self, adb_path: Optional[str] = None):
        """Initialize device manager.
        
        Args:
            adb_path: Path to ADB binary
        """
        self._adb = ADBWrapper(adb_path)
        self._devices: Dict[str, Device] = {}

    async def list_devices(self) -> List[Device]:
        """List connected devices.
        
        Returns:
            List of connected devices
        """
        devices_info = await self._adb.get_devices()
        
        # Update device cache
        current_serials = set()
        for device_info in devices_info:
            serial = device_info["serial"]
            current_serials.add(serial)
            
            if serial not in self._devices:
                self._devices[serial] = Device(serial, self._adb)
                
        # Remove disconnected devices
        for serial in list(self._devices.keys()):
            if serial not in current_serials:
                del self._devices[serial]
                
        return list(self._devices.values())

    async def get_device(self, serial: str | None = None) -> Optional[Device]:
        """Get a specific device.
        
        Args:
            serial: Device serial number
            
        Returns:
            Device instance if found, None otherwise
        """
        if serial and serial in self._devices:
            return self._devices[serial]
            
        # Try to find the device
        devices = await self.list_devices()
        for device in devices:
            if device.serial == serial or not serial:
                return device
                
        return None

    async def connect(self, host: str, port: int = 5555) -> Optional[Device]:
        """Connect to a device over TCP/IP.
        
        Args:
            host: Device IP address
            port: Device port
            
        Returns:
            Connected device instance
        """
        try:
            serial = await self._adb.connect(host, port)
            return await self.get_device(serial)
        except Exception:
            return None

    async def disconnect(self, serial: str) -> bool:
        """Disconnect from a device.
        
        Args:
            serial: Device serial number
            
        Returns:
            True if disconnected successfully
        """
        success = await self._adb.disconnect(serial)
        if success and serial in self._devices:
            del self._devices[serial]
        return success 