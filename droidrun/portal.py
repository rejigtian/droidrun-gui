"""
Portal APK management and device communication utilities.

This module handles downloading, installing, and managing the DroidRun Portal app
on Android devices. It also provides utilities for checking accessibility service
status and managing device communication modes (TCP and content provider).
"""

import asyncio
import contextlib
import os
import tempfile

import requests
from rich.console import Console

from droidrun.tools import AdbTools
from async_adbutils import AdbDevice, adb

REPO = "droidrun/droidrun-portal"
ASSET_NAME = "droidrun-portal"
GITHUB_API_HOSTS = ["https://api.github.com", "https://ungh.cc"]

VERSION_MAP_GIST_URL = "https://raw.githubusercontent.com/droidrun/gists/refs/heads/main/version_map_android.json"

PORTAL_PACKAGE_NAME = "com.droidrun.portal"
A11Y_SERVICE_NAME = (
    f"{PORTAL_PACKAGE_NAME}/com.droidrun.portal.service.DroidrunAccessibilityService"
)


def get_version_mapping(debug: bool = False) -> dict | None:
    try:
        response = requests.get(VERSION_MAP_GIST_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        if debug:
            print(f"Failed to fetch version mapping: {e}")
        return None


def _version_in_range(version: str, range_str: str) -> bool:
    if "-" not in range_str:
        return False
    try:
        start, end = range_str.split("-", 1)
        v_parts = [int(x) for x in version.split(".")]
        s_parts = [int(x) for x in start.split(".")]
        e_parts = [int(x) for x in end.split(".")]
        return s_parts <= v_parts <= e_parts
    except (ValueError, AttributeError):
        return False


def get_compatible_portal_version(droidrun_version: str, debug: bool = False) -> tuple[str | None, str, bool]:
    mapping = get_version_mapping(debug)
    if mapping is None:
        return (None, "", False)

    mappings = mapping.get("mappings", {})
    download_base = mapping.get("download_base", "https://github.com/droidrun/droidrun-portal/releases/download")

    # Try exact match first
    if droidrun_version in mappings:
        return (mappings[droidrun_version], download_base, True)

    # Try range match (e.g., "0.4.0-0.4.14": "1.0.0")
    for key, portal_version in mappings.items():
        if "-" in key and _version_in_range(droidrun_version, key):
            return (portal_version, download_base, True)

    return (None, download_base, True)


@contextlib.contextmanager
def download_versioned_portal_apk(version: str, download_base: str, debug: bool = False):
    """Download a specific Portal APK version."""
    console = Console()
    asset_url = f"{download_base}/{version}/{ASSET_NAME}-{version}.apk"

    console.print(f"Downloading Portal APK [bold]{version}[/bold]")
    if debug:
        console.print(f"Asset URL: {asset_url}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".apk")
    try:
        r = requests.get(asset_url, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)
        tmp.close()
        yield tmp.name
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def get_latest_release_assets(debug: bool = False):
    """
    Fetch the latest Portal APK release assets from GitHub.

    Args:
        debug: Enable debug logging

    Returns:
        List of asset dictionaries from the latest GitHub release

    Raises:
        requests.HTTPError: If the GitHub API request fails
    """
    for host in GITHUB_API_HOSTS:
        url = f"{host}/repos/{REPO}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            if debug:
                print(f"Using GitHub release on {host}")
            break

    response.raise_for_status()
    latest_release = response.json()

    if "release" in latest_release:
        assets = latest_release["release"]["assets"]
    else:
        assets = latest_release.get("assets", [])

    return assets


@contextlib.contextmanager
def download_portal_apk(debug: bool = False):
    """
    Download the latest Portal APK from GitHub releases.

    This context manager downloads the APK to a temporary file and yields
    the file path. The file is automatically deleted when the context exits.

    Args:
        debug: Enable debug logging

    Yields:
        str: Path to the downloaded APK file

    Raises:
        Exception: If the Portal APK asset is not found in the release
        requests.HTTPError: If the download fails
    """
    console = Console()
    assets = get_latest_release_assets(debug)

    asset_version = None
    asset_url = None
    for asset in assets:
        if (
            "browser_download_url" in asset
            and "name" in asset
            and asset["name"].startswith(ASSET_NAME)
        ):
            asset_url = asset["browser_download_url"]
            asset_version = asset["name"].split("-")[-1]
            asset_version = asset_version.removesuffix(".apk")
            break
        elif "downloadUrl" in asset and os.path.basename(
            asset["downloadUrl"]
        ).startswith(ASSET_NAME):
            asset_url = asset["downloadUrl"]
            asset_version: str = asset.get("name", os.path.basename(asset_url)).split(
                "-"
            )[-1]
            asset_version = asset_version.removesuffix(".apk")
            break
        else:
            if debug:
                print(asset)

    if not asset_url:
        raise Exception(f"Asset named '{ASSET_NAME}' not found in the latest release.")

    console.print(f"Found Portal APK [bold]{asset_version}[/bold]")
    if debug:
        console.print(f"Asset URL: {asset_url}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".apk")
    try:
        r = requests.get(asset_url, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)
        tmp.close()
        yield tmp.name
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


async def enable_portal_accessibility(
    device: AdbDevice, service_name: str = A11Y_SERVICE_NAME
):
    """
    Enable the Portal accessibility service on the device.

    Args:
        device: ADB device connection
        service_name: Full accessibility service name (default: Portal service)

    Note:
        This may fail on some devices due to security restrictions.
        Manual enablement may be required.
    """
    await device.shell(
        f"settings put secure enabled_accessibility_services {service_name}"
    )
    await device.shell("settings put secure accessibility_enabled 1")


async def check_portal_accessibility(
    device: AdbDevice, service_name: str = A11Y_SERVICE_NAME, debug: bool = False
) -> bool:
    """
    Check if the Portal accessibility service is enabled.

    Args:
        device: ADB device connection
        service_name: Full accessibility service name to check
        debug: Enable debug logging

    Returns:
        True if the accessibility service is enabled, False otherwise
    """
    a11y_services = await device.shell(
        "settings get secure enabled_accessibility_services"
    )
    if service_name not in a11y_services:
        if debug:
            print(a11y_services)
        return False

    a11y_enabled = await device.shell("settings get secure accessibility_enabled")
    if a11y_enabled != "1":
        if debug:
            print(a11y_enabled)
        return False

    return True


async def ping_portal(device: AdbDevice, debug: bool = False):
    """
    Ping the Droidrun Portal to check if it is installed and accessible.
    """
    try:
        packages = await device.list_packages()
    except Exception as e:
        raise Exception("Failed to list packages") from e

    if PORTAL_PACKAGE_NAME not in packages:
        if debug:
            print(packages)
        raise Exception("Portal is not installed on the device")

    if not await check_portal_accessibility(device, debug=debug):
        await device.shell("am start -a android.settings.ACCESSIBILITY_SETTINGS")
        raise Exception(
            "Droidrun Portal is not enabled as an accessibility service on the device"
        )


async def ping_portal_content(device: AdbDevice, debug: bool = False):
    """
    Test Portal accessibility via content provider.

    Args:
        device: ADB device connection
        debug: Enable debug logging

    Raises:
        Exception: If Portal is not reachable via content provider
    """
    try:
        state = await device.shell(
            "content query --uri content://com.droidrun.portal/state"
        )
        if "Row: 0 result=" not in state:
            raise Exception("Failed to get state from Droidrun Portal")
    except Exception as e:
        raise Exception("Droidrun Portal is not reachable") from e


async def ping_portal_tcp(device: AdbDevice, debug: bool = False):
    """
    Test Portal accessibility via TCP mode.

    Args:
        device: ADB device connection
        debug: Enable debug logging

    Raises:
        Exception: If Portal is not reachable via TCP or port forwarding fails
    """
    try:
        tools = AdbTools(serial=device.serial, use_tcp=True)
        await tools.connect()
    except Exception as e:
        raise Exception("Failed to setup TCP forwarding") from e


async def set_overlay_offset(device: AdbDevice, offset: int):
    """
    Set the overlay offset using the /overlay_offset portal content provider endpoint.
    """
    try:
        cmd = f'content insert --uri "content://com.droidrun.portal/overlay_offset" --bind offset:i:{offset}'
        await device.shell(cmd)
    except Exception as e:
        raise Exception("Error setting overlay offset") from e


async def toggle_overlay(device: AdbDevice, visible: bool):
    """Toggle the overlay visibility.

    Args:
        device: Device to toggle the overlay on
        visible: Whether to show the overlay

    throws:
        Exception: If the overlay toggle fails
    """
    try:
        visible_str = "true" if visible else "false"
        cmd = f'content insert --uri "content://com.droidrun.portal/overlay_visible" --bind visible:b:{visible_str}'
        await device.shell(cmd)
    except Exception as e:
        raise Exception("Failed to toggle overlay") from e


async def setup_keyboard(device: AdbDevice):
    """
    Set up the DroidRun keyboard as the default input method.
    Simple setup that just switches to DroidRun keyboard without saving/restoring.

    throws:
        Exception: If the keyboard setup fails
    """
    try:
        await device.shell("ime enable com.droidrun.portal/.input.DroidrunKeyboardIME")
        await device.shell("ime set com.droidrun.portal/.input.DroidrunKeyboardIME")
    except Exception as e:
        raise Exception("Error setting up keyboard") from e


async def disable_keyboard(
    device: AdbDevice,
    target_ime: str = "com.droidrun.portal/.input.DroidrunKeyboardIME",
):
    """
    Disable a specific IME (keyboard) and optionally switch to another.
    By default, disables the DroidRun keyboard.

    Args:
        target_ime: The IME package/activity to disable (default: DroidRun keyboard)

    Returns:
        bool: True if disabled successfully, False otherwise
    """
    try:
        await device.shell(f"ime disable {target_ime}")
        return True
    except Exception as e:
        raise Exception("Error disabling keyboard") from e


async def test():
    device = await adb.device()
    await ping_portal(device, debug=False)


if __name__ == "__main__":
    asyncio.run(test())
