"""
Device Manager - Handles Android device connections and management.
"""

from typing import Optional, List
from ..adb import Device, DeviceManager as ADBDeviceManager

class DeviceManager:
    """Manages Android device connections and operations."""
    
    def __init__(self):
        """Initialize the device manager."""
        self._manager = ADBDeviceManager()
        
    async def connect(self, ip_address: str, port: int = 5555) -> Optional[Device]:
        """Connect to an Android device over TCP/IP."""
        return await self._manager.connect(ip_address, port)
        
    async def disconnect(self, serial: str) -> bool:
        """Disconnect from an Android device."""
        return await self._manager.disconnect(serial)
        
    async def list_devices(self) -> List[Device]:
        """List all connected devices."""
        return await self._manager.list_devices()
        
    async def get_device(self, serial: str) -> Optional[Device]:
        """Get a specific device by serial number."""
        return await self._manager.get_device(serial)