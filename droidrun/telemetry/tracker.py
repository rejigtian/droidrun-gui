from posthog import Posthog
from pathlib import Path
from uuid import uuid4
from typing import TypedDict
import os
import logging
from .events import TelemetryEvent

logger = logging.getLogger("droidrun-telemetry")

PROJECT_API_KEY = "phc_XyD3HKIsetZeRkmnfaBughs8fXWYArSUFc30C0HmRiO"
HOST = "https://eu.i.posthog.com"
USER_ID_PATH = Path.home() / ".droidrun" / "user_id"

posthog = Posthog(
    project_api_key=PROJECT_API_KEY,
    host=HOST,
    disable_geoip=False,
)


def is_telemetry_enabled():
    telemetry_enabled = os.environ.get("DROIDRUN_TELEMETRY_ENABLED", "true")
    enabled = telemetry_enabled.lower() in ["true", "1", "yes", "y"]
    logger.debug(f"Telemetry enabled: {enabled}")
    return enabled


def get_user_id() -> str:
    try:
        if not USER_ID_PATH.exists():
            USER_ID_PATH.touch()
            USER_ID_PATH.write_text(str(uuid4()))
        logger.debug(f"User ID: {USER_ID_PATH.read_text()}")
        return USER_ID_PATH.read_text()
    except Exception as e:
        logger.error(f"Error getting user ID: {e}")
        return "unknown"


def capture(event: TelemetryEvent):
    try:
        if not is_telemetry_enabled():
            logger.debug(f"Telemetry disabled, skipping capture of {event}")
            return
        event_name = event.__class__.__name__
        posthog.capture(get_user_id(), event_name, event)
        logger.debug(f"Captured event: {event_name} with properties: {event}")
    except Exception as e:
        logger.error(f"Error capturing event: {e}")


def flush():
    try:
        if not is_telemetry_enabled():
            logger.debug(f"Telemetry disabled, skipping flush")
            return
        posthog.flush()
        logger.debug(f"Flushed telemetry data")
    except Exception as e:
        logger.error(f"Error flushing telemetry data: {e}")
