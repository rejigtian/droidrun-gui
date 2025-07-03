---
title: Adb
---

<a id="droidrun.adb.wrapper"></a>

# droidrun.adb.wrapper

ADB Wrapper - Lightweight wrapper around ADB for Android device control.

<a id="droidrun.adb.wrapper.ADBWrapper"></a>

## droidrun.adb.wrapper.ADBWrapper

```python
class ADBWrapper()
```

Lightweight wrapper around ADB for Android device control.

<a id="droidrun.adb.wrapper.ADBWrapper.__init__"></a>

#### \_\_init\_\_

```python
def __init__(adb_path: Optional[str] = None)
```

Initialize ADB wrapper.

**Arguments**:

- `adb_path` - Path to ADB binary (defaults to 'adb' in PATH)

<a id="droidrun.adb.wrapper.ADBWrapper.get_devices"></a>

#### get\_devices

```python
async def get_devices() -> List[Dict[str, str]]
```

Get list of connected devices.

**Returns**:

  List of device info dictionaries with 'serial' and 'status' keys

<a id="droidrun.adb.wrapper.ADBWrapper.connect"></a>

#### connect

```python
async def connect(host: str, port: int = 5555) -> str
```

Connect to a device over TCP/IP.

**Arguments**:

- `host` - Device IP address
- `port` - Device port
  

**Returns**:

  Device serial number (host:port)

<a id="droidrun.adb.wrapper.ADBWrapper.disconnect"></a>

#### disconnect

```python
async def disconnect(serial: str) -> bool
```

Disconnect from a device.

**Arguments**:

- `serial` - Device serial number
  

**Returns**:

  True if disconnected successfully

<a id="droidrun.adb.wrapper.ADBWrapper.shell"></a>

#### shell

```python
async def shell(
    serial: str, command: str, timeout: Optional[float] = None
) -> str
```

Run a shell command on the device.

**Arguments**:

- `serial` - Device serial number
- `command` - Shell command to run
- `timeout` - Command timeout in seconds
  

**Returns**:

  Command output

<a id="droidrun.adb.wrapper.ADBWrapper.get_properties"></a>

#### get\_properties

```python
async def get_properties(serial: str) -> Dict[str, str]
```

Get device properties.

**Arguments**:

- `serial` - Device serial number
  

**Returns**:

  Dictionary of device properties

<a id="droidrun.adb.wrapper.ADBWrapper.install_app"></a>

#### install\_app

```python
async def install_app(
    serial: str,
    apk_path: str,
    reinstall: bool = False,
    grant_permissions: bool = True
) -> Tuple[str, str]
```

Install an APK on the device.

**Arguments**:

- `serial` - Device serial number
- `apk_path` - Path to the APK file
- `reinstall` - Whether to reinstall if app exists
- `grant_permissions` - Whether to grant all permissions
  

**Returns**:

  Tuple of (stdout, stderr)

<a id="droidrun.adb.wrapper.ADBWrapper.pull_file"></a>

#### pull\_file

```python
async def pull_file(serial: str, device_path: str,
                    local_path: str) -> Tuple[str, str]
```

Pull a file from the device.

**Arguments**:

- `serial` - Device serial number
- `device_path` - Path on the device
- `local_path` - Path on the local machine
  

**Returns**:

  Tuple of (stdout, stderr)

<a id="droidrun.adb.device"></a>

# droidrun.adb.device

Device - High-level representation of an Android device.

<a id="droidrun.adb.device.Device"></a>

## droidrun.adb.device.Device

```python
class Device()
```

High-level representation of an Android device.

<a id="droidrun.adb.device.Device.__init__"></a>

#### \_\_init\_\_

```python
def __init__(serial: str, adb: ADBWrapper)
```

Initialize device.

**Arguments**:

- `serial` - Device serial number
- `adb` - ADB wrapper instance

<a id="droidrun.adb.device.Device.serial"></a>

#### serial

```python
def serial() -> str
```

Get device serial number.

<a id="droidrun.adb.device.Device.get_properties"></a>

#### get\_properties

```python
async def get_properties() -> Dict[str, str]
```

Get all device properties.

<a id="droidrun.adb.device.Device.get_property"></a>

#### get\_property

```python
async def get_property(name: str) -> str
```

Get a specific device property.

<a id="droidrun.adb.device.Device.model"></a>

#### model

```python
async def model() -> str
```

Get device model.

<a id="droidrun.adb.device.Device.brand"></a>

#### brand

```python
async def brand() -> str
```

Get device brand.

<a id="droidrun.adb.device.Device.android_version"></a>

#### android\_version

```python
async def android_version() -> str
```

Get Android version.

<a id="droidrun.adb.device.Device.sdk_level"></a>

#### sdk\_level

```python
async def sdk_level() -> str
```

Get SDK level.

<a id="droidrun.adb.device.Device.shell"></a>

#### shell

```python
async def shell(command: str, timeout: float | None = None) -> str
```

Execute a shell command on the device.

<a id="droidrun.adb.device.Device.tap"></a>

#### tap

```python
async def tap(x: int, y: int) -> None
```

Tap at coordinates.

**Arguments**:

- `x` - X coordinate
- `y` - Y coordinate

<a id="droidrun.adb.device.Device.swipe"></a>

#### swipe

```python
async def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 300
) -> None
```

Perform swipe gesture.

**Arguments**:

- `start_x` - Starting X coordinate
- `start_y` - Starting Y coordinate
- `end_x` - Ending X coordinate
- `end_y` - Ending Y coordinate
- `duration_ms` - Swipe duration in milliseconds

<a id="droidrun.adb.device.Device.input_text"></a>

#### input\_text

```python
async def input_text(text: str) -> None
```

Input text.

**Arguments**:

- `text` - Text to input

<a id="droidrun.adb.device.Device.press_key"></a>

#### press\_key

```python
async def press_key(keycode: int) -> None
```

Press a key.

**Arguments**:

- `keycode` - Android keycode to press

<a id="droidrun.adb.device.Device.start_activity"></a>

#### start\_activity

```python
async def start_activity(
    package: str,
    activity: str = ".MainActivity",
    extras: Optional[Dict[str, str]] = None
) -> None
```

Start an app activity.

**Arguments**:

- `package` - Package name
- `activity` - Activity name
- `extras` - Intent extras

<a id="droidrun.adb.device.Device.start_app"></a>

#### start\_app

```python
async def start_app(package: str, activity: str = "") -> str
```

Start an app on the device.

**Arguments**:

- `package` - Package name
- `activity` - Optional activity name (if empty, launches default activity)
  

**Returns**:

  Result message

<a id="droidrun.adb.device.Device.install_app"></a>

#### install\_app

```python
async def install_app(
    apk_path: str,
    reinstall: bool = False,
    grant_permissions: bool = True
) -> str
```

Install an APK on the device.

**Arguments**:

- `apk_path` - Path to the APK file
- `reinstall` - Whether to reinstall if app exists
- `grant_permissions` - Whether to grant all requested permissions
  

**Returns**:

  Installation result

<a id="droidrun.adb.device.Device.uninstall_app"></a>

#### uninstall\_app

```python
async def uninstall_app(package: str, keep_data: bool = False) -> str
```

Uninstall an app from the device.

**Arguments**:

- `package` - Package name to uninstall
- `keep_data` - Whether to keep app data and cache directories
  

**Returns**:

  Uninstallation result

<a id="droidrun.adb.device.Device.take_screenshot"></a>

#### take\_screenshot

```python
async def take_screenshot(quality: int = 75) -> Tuple[str, bytes]
```

Take a screenshot of the device and compress it.

**Arguments**:

- `quality` - JPEG quality (1-100, lower means smaller file size)
  

**Returns**:

  Tuple of (local file path, screenshot data as bytes)

<a id="droidrun.adb.device.Device.list_packages"></a>

#### list\_packages

```python
async def list_packages(include_system_apps: bool = False) -> List[str]
```

List installed packages on the device.

**Arguments**:

- `include_system_apps` - Whether to include system apps (default: False)
  

**Returns**:

  List of package names

<a id="droidrun.adb.manager"></a>

# droidrun.adb.manager

Device Manager - Manages Android device connections.

<a id="droidrun.adb.manager.DeviceManager"></a>

## droidrun.adb.manager.DeviceManager

```python
class DeviceManager()
```

Manages Android device connections.

<a id="droidrun.adb.manager.DeviceManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(adb_path: Optional[str] = None)
```

Initialize device manager.

**Arguments**:

- `adb_path` - Path to ADB binary

<a id="droidrun.adb.manager.DeviceManager.list_devices"></a>

#### list\_devices

```python
async def list_devices() -> List[Device]
```

List connected devices.

**Returns**:

  List of connected devices

<a id="droidrun.adb.manager.DeviceManager.get_device"></a>

#### get\_device

```python
async def get_device(serial: str | None = None) -> Optional[Device]
```

Get a specific device.

**Arguments**:

- `serial` - Device serial number
  

**Returns**:

  Device instance if found, None otherwise

<a id="droidrun.adb.manager.DeviceManager.connect"></a>

#### connect

```python
async def connect(host: str, port: int = 5555) -> Optional[Device]
```

Connect to a device over TCP/IP.

**Arguments**:

- `host` - Device IP address
- `port` - Device port
  

**Returns**:

  Connected device instance

<a id="droidrun.adb.manager.DeviceManager.disconnect"></a>

#### disconnect

```python
async def disconnect(serial: str) -> bool
```

Disconnect from a device.

**Arguments**:

- `serial` - Device serial number
  

**Returns**:

  True if disconnected successfully

