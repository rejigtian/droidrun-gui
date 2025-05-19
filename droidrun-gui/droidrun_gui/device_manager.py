import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class DeviceManager(QObject):
    device_connected = pyqtSignal(str)
    device_disconnected = pyqtSignal(str)
    device_status_changed = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.data_dir = Path.home() / ".droidrun-gui"
        self.data_dir.mkdir(exist_ok=True)
        self.devices_file = self.data_dir / "devices.json"
        self._load_devices()
        
    def _load_devices(self):
        if self.devices_file.exists():
            with open(self.devices_file, 'r', encoding='utf-8') as f:
                self.devices = json.load(f)
        else:
            self.devices = {}
            
    def _save_devices(self):
        with open(self.devices_file, 'w', encoding='utf-8') as f:
            json.dump(self.devices, f, ensure_ascii=False, indent=2)
            
    def get_connected_devices(self) -> List[str]:
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            devices = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip() and 'device' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
                    if device_id not in self.devices:
                        self.devices[device_id] = {
                            "name": self._get_device_name(device_id),
                            "model": self._get_device_model(device_id),
                            "status": "connected"
                        }
                        self.device_connected.emit(device_id)
            self._save_devices()
            return devices
        except Exception as e:
            print(f"Error getting devices: {e}")
            return []
            
    def _get_device_name(self, device_id: str) -> str:
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.device'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        except:
            return "Unknown Device"
            
    def _get_device_model(self, device_id: str) -> str:
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        except:
            return "Unknown Model"
            
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        return self.devices.get(device_id)
        
    def connect_device(self, ip_address: str) -> bool:
        try:
            result = subprocess.run(
                ['adb', 'connect', ip_address],
                capture_output=True, text=True
            )
            return "connected" in result.stdout.lower()
        except:
            return False
            
    def disconnect_device(self, device_id: str) -> bool:
        try:
            result = subprocess.run(
                ['adb', 'disconnect', device_id],
                capture_output=True, text=True
            )
            if device_id in self.devices:
                del self.devices[device_id]
                self._save_devices()
                self.device_disconnected.emit(device_id)
            return True
        except:
            return False
            
    def get_device_battery(self, device_id: str) -> Optional[int]:
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'dumpsys', 'battery'],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if 'level' in line:
                    return int(line.split(':')[1].strip())
        except:
            return None
            
    def get_device_storage(self, device_id: str) -> Optional[Dict]:
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'df', '/data'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    return {
                        "total": int(parts[1]),
                        "used": int(parts[2]),
                        "free": int(parts[3])
                    }
        except:
            return None 