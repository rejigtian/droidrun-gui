#!/usr/bin/env python3
"""
Minimal keepalive script for DroidRun overlay toggling.
"""

import subprocess
import time
import logging
import os
import argparse
import sys
import signal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Handle termination gracefully
def signal_handler(sig, frame):
    logger.info("Received termination signal, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description="Keep DroidRun overlay disabled")
    parser.add_argument("--adb-path", type=str, help="Path to ADB executable")
    parser.add_argument("--device-serial", type=str, help="Device serial number")
    parser.add_argument("--interval", type=int, default=5, help="Interval in seconds between commands")
    args = parser.parse_args()

    # Find ADB path if not specified
    adb_path = args.adb_path or 'adb'  # Default to system adb if not specified
    
    # Get first device if serial not specified
    device_serial = args.device_serial
    if not device_serial:
        try:
            result = subprocess.run([adb_path, "devices"], capture_output=True, text=True, check=True)
            devices = [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip() and "device" in line]
            if devices:
                device_serial = devices[0]
                logger.info(f"Using first available device: {device_serial}")
            else:
                logger.error("No devices found. Please connect a device or specify --device-serial.")
                return
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list devices: {e}")
            return

    interval = args.interval
    logger.info(f"Starting keepalive script with {interval} second interval")
    logger.info(f"ADB path: {adb_path}")
    logger.info(f"Device serial: {device_serial}")

    while True:
        try:
            cmd = [
                adb_path,
                "-s", device_serial,
                "shell",
                "am broadcast -a com.droidrun.portal.TOGGLE_OVERLAY --ez overlay_visible false"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(interval)
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            break

if __name__ == "__main__":
    main()
