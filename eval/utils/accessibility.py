"""
Accessibility service management for AndroidWorld benchmarks.
"""

import asyncio
import logging

logger = logging.getLogger("android_world_bench")

async def enable_accessibility_service(adb_path: str, device_serial: str, 
                                      service_name: str, disable_first: bool = False):
    """Enable the DroidRun accessibility service.
    
    This is crucial for DroidRun to function correctly with Android UI interactions.
    
    Args:
        adb_path: Path to ADB executable
        device_serial: Device serial number
        service_name: Name of the accessibility service to enable
        disable_first: Whether to disable all other accessibility services first
            
    Returns:
        bool: True if successful, False otherwise
    """
    if not device_serial:
        logger.error("Device serial not available for enabling accessibility service")
        return False
            
    logger.info(f"Configuring accessibility service: {service_name}")
        
    try:
        # Helper function to run ADB commands
        async def run_adb_command(cmd_args, step_name):
            logger.debug(f"Running ADB command ({step_name}): {' '.join(cmd_args)}")
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
                
            if process.returncode != 0:
                logger.error(f"Failed to {step_name}. Return code: {process.returncode}")
                if stdout_str: logger.error(f"Stdout: {stdout_str}")
                if stderr_str: logger.error(f"Stderr: {stderr_str}")
                return False
            else:
                logger.debug(f"Successfully {step_name}.")
                if stdout_str: logger.debug(f"Stdout: {stdout_str}")
                if stderr_str: logger.debug(f"Stderr: {stderr_str}")
                return True
            
        # Step 1: Disable all accessibility services if requested
        if disable_first:
            disable_cmd = [
                adb_path, 
                "-s", device_serial, 
                "shell", 
                "settings", 
                "put", 
                "secure", 
                "enabled_accessibility_services", 
                "''"
            ]
            if not await run_adb_command(disable_cmd, "disable all accessibility services"):
                logger.warning("Could not disable accessibility services, proceeding anyway...")
            else:
                logger.info("Disabled all accessibility services")
            await asyncio.sleep(2)  # Wait for services to be disabled
            
        # Step 2: Enable our specific accessibility service
        enable_service_cmd = [
            adb_path, 
            "-s", device_serial, 
            "shell", 
            "settings", 
            "put", 
            "secure", 
            "enabled_accessibility_services", 
            service_name
        ]
        if not await run_adb_command(enable_service_cmd, f"enable service {service_name}"):
            return False  # Critical failure
            
        await asyncio.sleep(1)  # Short delay
            
        # Step 3: Enable accessibility globally
        enable_global_cmd = [
            adb_path, 
            "-s", device_serial, 
            "shell", 
            "settings", 
            "put", 
            "secure", 
            "accessibility_enabled", 
            "1"
        ]
        if not await run_adb_command(enable_global_cmd, "enable accessibility globally"):
            return False  # Critical failure
            
        await asyncio.sleep(1)  # Short delay
            
        # Step 4: Disable overlay/box rendering if available
        disable_overlay_cmd = [
            adb_path, 
            "-s", device_serial, 
            "shell", 
            "am", 
            "broadcast", 
            "-a", 
            "com.droidrun.portal.TOGGLE_OVERLAY", 
            "--ez", 
            "overlay_visible", 
            "false"
        ]
        if not await run_adb_command(disable_overlay_cmd, "disable box rendering overlay"):
            logger.warning("Could not disable box rendering overlay, proceeding anyway...")
            
        logger.info(f"Successfully configured accessibility service: {service_name}")
        return True
            
    except FileNotFoundError:
        logger.error(f"ADB not found at path: {adb_path}")
        return False
    except Exception as e:
        logger.exception(f"Error enabling accessibility service: {e}")
        return False 