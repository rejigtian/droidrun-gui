"""
Tracing setup utility for DroidAgent.

This module provides a centralized way to configure tracing providers
(Phoenix, Langfuse, etc.) based on the TracingConfig.
"""

import logging
import os
from typing import Optional
from uuid import uuid4

import llama_index.core

from droidrun.config_manager.config_manager import TracingConfig

logger = logging.getLogger("droidrun")

# Module-level variable to store session_id across DroidAgent invocations
_session_id: Optional[str] = None


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
    global _session_id

    try:
        # Set environment variables if provided in config
        if tracing_config.langfuse_secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = tracing_config.langfuse_secret_key
        if tracing_config.langfuse_public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = tracing_config.langfuse_public_key
        if tracing_config.langfuse_host:
            os.environ["LANGFUSE_HOST"] = tracing_config.langfuse_host
        else:
            # Default to US cloud if not specified
            os.environ["LANGFUSE_HOST"] = "https://us.cloud.langfuse.com"

        # Initialize Langfuse client and verify connection
        from langfuse import Langfuse

        langfuse = Langfuse()
        if not langfuse.auth_check():
            logger.error(
                "❌ Langfuse authentication failed. Please check your credentials."
            )
            return

        # Initialize OpenInference LlamaIndex instrumentation
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

        LlamaIndexInstrumentor().instrument()

        # Generate or use configured session_id
        if tracing_config.langfuse_session_id:
            # Use configured session_id
            _session_id = tracing_config.langfuse_session_id
        else:
            # Auto-generate UUID
            _session_id = str(uuid4())

        # Set session_id and user_id globally for the process
        from opentelemetry.context import attach, get_current, set_value
        from openinference.semconv.trace import SpanAttributes

        ctx = get_current()
        ctx = set_value(SpanAttributes.SESSION_ID, _session_id, ctx)
        if tracing_config.langfuse_user_id:
            ctx = set_value(
                SpanAttributes.USER_ID, tracing_config.langfuse_user_id, ctx
            )
        attach(ctx)

        logger.info(
            f"🔍 Langfuse tracing enabled via OpenInference instrumentation\n"
            f"    Session ID: {_session_id}\n"
            f"    User ID: {tracing_config.langfuse_user_id}\n"
            f"    Host: {os.environ.get('LANGFUSE_HOST')}"
        )
    except ImportError as e:
        logger.warning(
            "⚠️  Langfuse dependencies are not installed.\n"
            "    To enable Langfuse integration, install with:\n"
            "    • If installed via tool: `uv tool install droidrun[langfuse]`\n"
            "    • If installed via pip: `uv pip install droidrun[langfuse]`\n"
            f"    Missing: {e.name if hasattr(e, 'name') else str(e)}\n"
        )
