"""
DroidRun Tools - Core functionality for Android device control.
"""

from .device import DeviceManager
from .actions import (
    tap,
    swipe,
    input_text,
    press_key,
    start_app,
    install_app,
    uninstall_app,
    take_screenshot,
    list_packages,
    get_clickables,
    complete,
    extract,
    get_phone_state
)
from .remember import remember

__all__ = [
    'DeviceManager',
    'tap',
    'swipe',
    'input_text',
    'press_key',
    'start_app',
    'install_app',
    'uninstall_app',
    'take_screenshot',
    'list_packages',
    'get_clickables',
    'complete',
    'extract',
    'remember',
    'get_phone_state'
]