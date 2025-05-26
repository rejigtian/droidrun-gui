"""
Keepalive service for the DroidRun accessibility overlay.

This module provides functionality to continuously disable the overlay of the
DroidRun accessibility service, which is necessary for some tasks.
"""

import os
import sys
import time
import logging
import asyncio
import subprocess
from typing import Optional

logger = logging.getLogger("android_world_bench")

class OverlayKeepalive:
    """Manages the keepalive service for disabling the DroidRun overlay."""
    
    def __init__(
        self, 
        adb_path: str = "adb", 
        device_serial: Optional[str] = None,
        interval: int = 5
    ):
        """Initialize the keepalive service.
        
        Args:
            adb_path: Path to ADB executable
            device_serial: Device serial number
            interval: Interval in seconds between commands
        """
        self.adb_path = adb_path
        self.device_serial = device_serial
        self.interval = interval
        self.process = None
        self.running = False
    
    def start(self):
        """Start the keepalive service as a subprocess."""
        if self.process and self.process.poll() is None:
            logger.info("Keepalive service is already running")
            return
        
        # Path to the script file
        script_path = os.path.join(os.path.dirname(__file__), "keepalive_script.py")
        
        # Write the script file if it doesn't exist
        if not os.path.exists(script_path):
            self._create_script_file(script_path)
        
        # Build command
        cmd = [sys.executable, script_path]
        if self.adb_path:
            cmd.extend(["--adb-path", self.adb_path])
        if self.device_serial:
            cmd.extend(["--device-serial", self.device_serial])
        cmd.extend(["--interval", str(self.interval)])
        
        # Start the process
        try:
            logger.info(f"Starting keepalive service with interval {self.interval}s")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self.running = True
            logger.info(f"Keepalive service started (PID: {self.process.pid})")
        except Exception as e:
            logger.error(f"Failed to start keepalive service: {e}")
    
    def stop(self):
        """Stop the keepalive service."""
        if not self.process:
            logger.info("No keepalive service to stop")
            return
        
        try:
            logger.info("Stopping keepalive service")
            self.process.terminate()
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=5)
                logger.info("Keepalive service stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Keepalive service did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
                logger.info("Keepalive service killed")
            
            self.process = None
            self.running = False
        except Exception as e:
            logger.error(f"Error stopping keepalive service: {e}")
    
    def _create_script_file(self, script_path: str):
        """Create the keepalive script file.
        
        Args:
            script_path: Path to write the script to
        """
        script_content = '''#!/usr/bin/env python3
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
'''
        
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            logger.info(f"Created keepalive script at {script_path}")
        except Exception as e:
            logger.error(f"Failed to create keepalive script: {e}")

async def disable_overlay_once(adb_path: str, device_serial: str):
    """Disable the overlay once.
    
    Args:
        adb_path: Path to ADB executable
        device_serial: Device serial number
    """
    try:
        cmd = [
            adb_path,
            "-s", device_serial,
            "shell",
            "am broadcast -a com.droidrun.portal.TOGGLE_OVERLAY --ez overlay_visible false"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        logger.debug("Disabled overlay once")
        return True
    except Exception as e:
        logger.error(f"Failed to disable overlay: {e}")
        return False 