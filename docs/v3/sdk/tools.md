---
title: Tools
---

<a id="droidrun.tools.ios"></a>

# droidrun.tools.ios

UI Actions - Core UI interaction tools for iOS device control.

<a id="droidrun.tools.ios.IOSTools"></a>

## droidrun.tools.ios.IOSTools

```python
class IOSTools(Tools)
```

Core UI interaction tools for iOS device control.

<a id="droidrun.tools.ios.IOSTools.get_state"></a>

#### get\_state

```python
async def get_state(serial: Optional[str] = None) -> List[Dict[str, Any]]
```

Get all clickable UI elements from the iOS device using accessibility API.

**Arguments**:

- `serial` - Optional device URL (not used for iOS, uses instance URL)
  

**Returns**:

  List of dictionaries containing UI elements extracted from the device screen

<a id="droidrun.tools.ios.IOSTools.tap_by_index"></a>

#### tap\_by\_index

```python
async def tap_by_index(index: int, serial: Optional[str] = None) -> str
```

Tap on a UI element by its index.

This function uses the cached clickable elements
to find the element with the given index and tap on its center coordinates.

**Arguments**:

- `index` - Index of the element to tap
  

**Returns**:

  Result message

<a id="droidrun.tools.ios.IOSTools.tap"></a>

#### tap

```python
async def tap(index: int) -> str
```

Tap on a UI element by its index.

This function uses the cached clickable elements from the last get_clickables call
to find the element with the given index and tap on its center coordinates.

**Arguments**:

- `index` - Index of the element to tap
  

**Returns**:

  Result message

<a id="droidrun.tools.ios.IOSTools.swipe"></a>

#### swipe

```python
async def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 300
) -> bool
```

Performs a straight-line swipe gesture on the device screen.
To perform a hold (long press), set the start and end coordinates to the same values and increase the duration as needed.

**Arguments**:

- `start_x` - Starting X coordinate
- `start_y` - Starting Y coordinate
- `end_x` - Ending X coordinate
- `end_y` - Ending Y coordinate
- `duration_ms` - Duration of swipe in milliseconds (not used in iOS API)

**Returns**:

  Bool indicating success or failure

<a id="droidrun.tools.ios.IOSTools.input_text"></a>

#### input\_text

```python
async def input_text(text: str, serial: Optional[str] = None) -> str
```

Input text on the iOS device.

**Arguments**:

- `text` - Text to input. Can contain spaces, newlines, and special characters including non-ASCII.
- `serial` - Optional device serial (not used for iOS, uses instance URL)
  

**Returns**:

  Result message

<a id="droidrun.tools.ios.IOSTools.press_key"></a>

#### press\_key

```python
async def press_key(keycode: int) -> str
```

Press a key on the iOS device.

iOS Key codes:
- 0: HOME
- 4: ACTION
- 5: CAMERA

**Arguments**:

- `keycode` - iOS keycode to press

<a id="droidrun.tools.ios.IOSTools.start_app"></a>

#### start\_app

```python
async def start_app(package: str, activity: str = "") -> str
```

Start an app on the iOS device.

**Arguments**:

- `package` - Bundle identifier (e.g., "com.apple.MobileSMS")
- `activity` - Optional activity name (not used on iOS)

<a id="droidrun.tools.ios.IOSTools.take_screenshot"></a>

#### take\_screenshot

```python
async def take_screenshot() -> Tuple[str, bytes]
```

Take a screenshot of the iOS device.
This function captures the current screen and adds the screenshot to context in the next message.
Also stores the screenshot in the screenshots list with timestamp for later GIF creation.

<a id="droidrun.tools.ios.IOSTools.get_phone_state"></a>

#### get\_phone\_state

```python
async def get_phone_state(serial: Optional[str] = None) -> Dict[str, Any]
```

Get the current phone state including current activity and keyboard visibility.

**Arguments**:

- `serial` - Optional device serial number (not used for iOS)
  

**Returns**:

  Dictionary with current phone state information

<a id="droidrun.tools.ios.IOSTools.remember"></a>

#### remember

```python
async def remember(information: str) -> str
```

Store important information to remember for future context.

This information will be included in future LLM prompts to help maintain context
across interactions. Use this for critical facts, observations, or user preferences
that should influence future decisions.

**Arguments**:

- `information` - The information to remember
  

**Returns**:

  Confirmation message

<a id="droidrun.tools.ios.IOSTools.get_memory"></a>

#### get\_memory

```python
def get_memory() -> List[str]
```

Retrieve all stored memory items.

**Returns**:

  List of stored memory items

<a id="droidrun.tools.ios.IOSTools.complete"></a>

#### complete

```python
def complete(success: bool, reason: str = "")
```

Mark the task as finished.

**Arguments**:

- `success` - Indicates if the task was successful.
- `reason` - Reason for failure/success

<a id="droidrun.tools.tools"></a>

# droidrun.tools.tools

<a id="droidrun.tools.tools.describe_tools"></a>

#### droidrun.tools.tools.describe\_tools

```python
def describe_tools(tools: Tools) -> Dict[str, Callable[..., Any]]
```

Describe the tools available for the given Tools instance.

**Arguments**:

- `tools` - The Tools instance to describe.
  

**Returns**:

  A dictionary mapping tool names to their descriptions.

<a id="droidrun.tools.adb"></a>

# droidrun.tools.adb

UI Actions - Core UI interaction tools for Android device control.

<a id="droidrun.tools.adb.AdbTools"></a>

## droidrun.tools.adb.AdbTools

```python
class AdbTools(Tools)
```

Core UI interaction tools for Android device control.

<a id="droidrun.tools.adb.AdbTools.get_device_serial"></a>

#### get\_device\_serial

```python
def get_device_serial() -> str
```

Get the device serial from the instance or environment variable.

<a id="droidrun.tools.adb.AdbTools.get_device"></a>

#### get\_device

```python
async def get_device() -> Optional[Device]
```

Get the device instance using the instance's serial or from environment variable.

**Returns**:

  Device instance or None if not found

<a id="droidrun.tools.adb.AdbTools.tap_by_index"></a>

#### tap\_by\_index

```python
async def tap_by_index(index: int, serial: Optional[str] = None) -> str
```

Tap on a UI element by its index.

This function uses the cached clickable elements
to find the element with the given index and tap on its center coordinates.

**Arguments**:

- `index` - Index of the element to tap
  

**Returns**:

  Result message

<a id="droidrun.tools.adb.AdbTools.tap_by_coordinates"></a>

#### tap\_by\_coordinates

```python
async def tap_by_coordinates(x: int, y: int) -> bool
```

Tap on the device screen at specific coordinates.

**Arguments**:

- `x` - X coordinate
- `y` - Y coordinate
  

**Returns**:

  Bool indicating success or failure

<a id="droidrun.tools.adb.AdbTools.tap"></a>

#### tap

```python
async def tap(index: int) -> str
```

Tap on a UI element by its index.

This function uses the cached clickable elements from the last get_clickables call
to find the element with the given index and tap on its center coordinates.

**Arguments**:

- `index` - Index of the element to tap
  

**Returns**:

  Result message

<a id="droidrun.tools.adb.AdbTools.swipe"></a>

#### swipe

```python
async def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 300
) -> bool
```

Performs a straight-line swipe gesture on the device screen.
To perform a hold (long press), set the start and end coordinates to the same values and increase the duration as needed.

**Arguments**:

- `start_x` - Starting X coordinate
- `start_y` - Starting Y coordinate
- `end_x` - Ending X coordinate
- `end_y` - Ending Y coordinate
- `duration_ms` - Duration of swipe in milliseconds

**Returns**:

  Bool indicating success or failure

<a id="droidrun.tools.adb.AdbTools.input_text"></a>

#### input\_text

```python
async def input_text(text: str, serial: Optional[str] = None) -> str
```

Input text on the device.
Always make sure that the Focused Element is not None before inputting text.

**Arguments**:

- `text` - Text to input. Can contain spaces, newlines, and special characters including non-ASCII.
  

**Returns**:

  Result message

<a id="droidrun.tools.adb.AdbTools.back"></a>

#### back

```python
async def back() -> str
```

Go back on the current view.
This presses the Android back button.

<a id="droidrun.tools.adb.AdbTools.press_key"></a>

#### press\_key

```python
async def press_key(keycode: int) -> str
```

Press a key on the Android device.

Common keycodes:
- 3: HOME
- 4: BACK
- 66: ENTER
- 67: DELETE

**Arguments**:

- `keycode` - Android keycode to press

<a id="droidrun.tools.adb.AdbTools.start_app"></a>

#### start\_app

```python
async def start_app(package: str, activity: str = "") -> str
```

Start an app on the device.

**Arguments**:

- `package` - Package name (e.g., "com.android.settings")
- `activity` - Optional activity name

<a id="droidrun.tools.adb.AdbTools.install_app"></a>

#### install\_app

```python
async def install_app(
    apk_path: str,
    reinstall: bool = False,
    grant_permissions: bool = True
) -> str
```

Install an app on the device.

**Arguments**:

- `apk_path` - Path to the APK file
- `reinstall` - Whether to reinstall if app exists
- `grant_permissions` - Whether to grant all permissions

<a id="droidrun.tools.adb.AdbTools.take_screenshot"></a>

#### take\_screenshot

```python
async def take_screenshot() -> Tuple[str, bytes]
```

Take a screenshot of the device.
This function captures the current screen and adds the screenshot to context in the next message.
Also stores the screenshot in the screenshots list with timestamp for later GIF creation.

<a id="droidrun.tools.adb.AdbTools.list_packages"></a>

#### list\_packages

```python
async def list_packages(include_system_apps: bool = False) -> List[str]
```

List installed packages on the device.

**Arguments**:

- `include_system_apps` - Whether to include system apps (default: False)
  

**Returns**:

  List of package names

<a id="droidrun.tools.adb.AdbTools.complete"></a>

#### complete

```python
def complete(success: bool, reason: str = "")
```

Mark the task as finished.

**Arguments**:

- `success` - Indicates if the task was successful.
- `reason` - Reason for failure/success

<a id="droidrun.tools.adb.AdbTools.remember"></a>

#### remember

```python
async def remember(information: str) -> str
```

Store important information to remember for future context.

This information will be extracted and included into your next steps to maintain context
across interactions. Use this for critical facts, observations, or user preferences
that should influence future decisions.

**Arguments**:

- `information` - The information to remember
  

**Returns**:

  Confirmation message

<a id="droidrun.tools.adb.AdbTools.get_memory"></a>

#### get\_memory

```python
def get_memory() -> List[str]
```

Retrieve all stored memory items.

**Returns**:

  List of stored memory items

<a id="droidrun.tools.adb.AdbTools.get_state"></a>

#### get\_state

```python
async def get_state(serial: Optional[str] = None) -> Dict[str, Any]
```

Get both the a11y tree and phone state in a single call using the combined /state endpoint.

**Arguments**:

- `serial` - Optional device serial number
  

**Returns**:

  Dictionary containing both 'a11y_tree' and 'phone_state' data

