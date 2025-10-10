"""
Backend configuration for DroidRun web interface.

This module provides configuration settings for the backend server.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BackendConfig(BaseSettings):
    """Configuration for DroidRun backend."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Enable auto-reload in development")
    log_level: str = Field(default="info", description="Logging level")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["*"], description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")

    # Session management
    max_session_age_hours: int = Field(
        default=24, description="Maximum age for sessions before cleanup"
    )
    cleanup_interval_hours: int = Field(
        default=6, description="Interval for automatic session cleanup"
    )

    # Event streaming
    event_queue_size: int = Field(
        default=1000, description="Maximum size of event queues"
    )
    sse_keepalive_seconds: int = Field(
        default=30, description="SSE keepalive interval"
    )
    websocket_ping_interval: int = Field(
        default=30, description="WebSocket ping interval"
    )

    # Agent execution
    max_concurrent_agents: int = Field(
        default=10, description="Maximum concurrent agent executions"
    )

    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")

    class Config:
        env_prefix = "DROIDRUN_BACKEND_"
        env_file = ".env"
        case_sensitive = False


# Global config instance
_config: Optional[BackendConfig] = None


def get_config() -> BackendConfig:
    """
    Get the global backend configuration.

    Returns:
        BackendConfig instance
    """
    global _config
    if _config is None:
        _config = BackendConfig()
    return _config


def load_config(config_path: Optional[str] = None) -> BackendConfig:
    """
    Load configuration from file.

    Args:
        config_path: Optional path to configuration file

    Returns:
        BackendConfig instance
    """
    global _config
    if config_path:
        _config = BackendConfig(_env_file=config_path)
    else:
        _config = BackendConfig()
    return _config
