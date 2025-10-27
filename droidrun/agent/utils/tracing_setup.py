"""
Tracing setup utility for DroidAgent.

This module provides a centralized way to configure tracing providers
(Phoenix, Langfuse, etc.) based on the TracingConfig.
"""

import logging
import os
from uuid import uuid4

import llama_index.core

from droidrun.config_manager.config_manager import TracingConfig

logger = logging.getLogger("droidrun")


def setup_tracing(tracing_config: TracingConfig) -> None:
    """
    Set up tracing based on the provided TracingConfig.

    Args:
        tracing_config: TracingConfig instance containing tracing settings

    Raises:
        ImportError: If the specified tracing provider is not installed
    """
    if not tracing_config.enabled:
        return

    provider = tracing_config.provider.lower()

    if provider == "phoenix":
        _setup_phoenix_tracing()
    elif provider == "langfuse":
        _setup_langfuse_tracing(tracing_config)
    else:
        logger.warning(
            f"⚠️  Unknown tracing provider: {provider}. "
            f"Supported providers: phoenix, langfuse"
        )


def _setup_phoenix_tracing() -> None:
    """Set up Arize Phoenix tracing."""
    try:
        from droidrun.telemetry.phoenix import arize_phoenix_callback_handler

        handler = arize_phoenix_callback_handler()
        llama_index.core.global_handler = handler
        llama_index.core.set_global_handler
        logger.info("🔍 Arize Phoenix tracing enabled globally")
    except ImportError:
        logger.warning(
            "⚠️  Arize Phoenix is not installed.\n"
            "    To enable Phoenix integration, install with:\n"
            "    • If installed via tool: `uv tool install droidrun[phoenix]`"
            "    • If installed via pip: `uv pip install droidrun[phoenix]`\n"
        )


def _setup_langfuse_tracing(tracing_config: TracingConfig) -> None:
    """
    Set up Langfuse tracing.

    Args:
        tracing_config: TracingConfig instance containing Langfuse credentials
    """
    try:
        # Set environment variables if provided in config
        if tracing_config.langfuse_secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = tracing_config.langfuse_secret_key
        if tracing_config.langfuse_public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = tracing_config.langfuse_public_key
        if tracing_config.langfuse_host:
            os.environ["LANGFUSE_HOST"] = tracing_config.langfuse_host
        os.environ["LANGFUSE_FLUSH_AT"] = "5"
        os.environ["LANGFUSE_FLUSH_INTERVAL"] = "1"

        from llama_index.core import set_global_handler

        session_id = str(uuid4())
        set_global_handler(
            "langfuse",
            user_id=tracing_config.langfuse_user_id,
            session_id=session_id
        )
        logger.info(f"🔍 Langfuse tracing enabled globally (session: {session_id})")
    except ImportError:
        logger.warning(
            "⚠️  Langfuse is not installed.\n"
            "    To enable Langfuse integration, install with:\n"
            "    • If installed via tool: `uv tool install droidrun[langfuse]`\n"
            "    • If installed via pip: `uv pip install droidrun[langfuse]`\n"
        )
