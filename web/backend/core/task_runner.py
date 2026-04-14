"""
Task runner — executes a DroidAgent task using a WebSocketDevice.
Streams log lines to an asyncio.Queue so they can be forwarded via SSE.
"""

import asyncio
import logging
import os
from typing import Callable, Optional

from db.database import AsyncSessionLocal
from db.models import Task, TaskLog
from ws.portal_ws import connected_devices
from agent.ws_device import WebSocketDevice
from core.settings_manager import get as cfg

logger = logging.getLogger(__name__)


async def run_task(
    task_id: str,
    goal: str,
    device_id: str,
    log_queue: asyncio.Queue,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
    enable_vision: bool = False,
    enable_reasoning: bool = False,
) -> dict:
    """
    Execute a DroidAgent task against a Portal-connected device.

    Args:
        task_id:          DB task ID (for updating status/logs)
        goal:             Task description
        device_id:        Target device ID (must be in connected_devices)
        log_queue:        asyncio.Queue — put log strings here for SSE streaming
        provider_override: Use this provider instead of the global default
        model_override:   Use this model instead of the global default
        enable_vision:    Pass to FastAgentConfig/ManagerConfig/ExecutorConfig
        enable_reasoning: Pass to AgentConfig.reasoning

    Returns:
        {"success": bool, "reason": str, "steps": int}
    """

    async def log(msg: str):
        await log_queue.put(msg)
        async with AsyncSessionLocal() as session:
            session.add(TaskLog(task_id=task_id, message=msg))
            await session.commit()

    # ------------------------------------------------------------------ #
    # Check device connection
    # ------------------------------------------------------------------ #
    conn = connected_devices.get(device_id)
    if conn is None or not conn.is_connected:
        msg = f"Device {device_id} is not connected"
        await log(f"❌ {msg}")
        return {"success": False, "reason": msg, "steps": 0}

    try:
        # ------------------------------------------------------------------ #
        # Import droidrun
        # ------------------------------------------------------------------ #
        try:
            from droidrun import DroidAgent
            from droidrun.config_manager import (
                DroidConfig,
                AgentConfig,
                DeviceConfig,
                LLMProfile,
                FastAgentConfig,
                ManagerConfig,
                ExecutorConfig,
            )
        except ImportError as e:
            msg = f"droidrun not installed: {e}"
            await log(f"❌ {msg}")
            return {"success": False, "reason": msg, "steps": 0}

        # ------------------------------------------------------------------ #
        # Build LLMProfile from settings
        # ------------------------------------------------------------------ #
        provider = provider_override or cfg("default_provider", "GoogleGenAI")
        await log(f"📝 Provider: {provider}")

        model_map = {
            "GoogleGenAI": cfg("gemini_model", "gemini-2.0-flash"),
            "OpenAI": cfg("openai_model", "gpt-4o"),
            "Anthropic": cfg("anthropic_model", "claude-sonnet-4-6"),
            "DeepSeek": cfg("deepseek_model", "deepseek-chat"),
            "ZhipuAI": cfg("zhipu_model", "glm-4-plus"),
            "Ollama": cfg("ollama_model", "llama3.2"),
        }
        model = model_override or model_map.get(provider, "gemini-2.0-flash")
        await log(f"🤖 Model: {model}")

        actual_provider = provider
        base_url = None
        api_key = None

        if provider == "GoogleGenAI":
            api_key = cfg("google_api_key", "") or os.environ.get("GOOGLE_API_KEY", "")
            if api_key:
                os.environ["GOOGLE_API_KEY"] = api_key
        elif provider == "OpenAI":
            api_key = cfg("openai_api_key", "") or os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "Anthropic":
            api_key = cfg("anthropic_api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
        elif provider == "DeepSeek":
            api_key = cfg("deepseek_api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")
            if api_key:
                os.environ["DEEPSEEK_API_KEY"] = api_key
        elif provider == "ZhipuAI":
            actual_provider = "OpenAILike"
            base_url = "https://open.bigmodel.cn/api/paas/v4"
            api_key = cfg("zhipu_api_key", "") or os.environ.get("ZHIPUAI_API_KEY", "")
        elif provider == "Ollama":
            actual_provider = "OpenAILike"
            base_url = cfg("ollama_base_url", "http://localhost:11434")

        profile_kwargs: dict = {}
        if api_key:
            profile_kwargs["api_key"] = api_key
        if not api_key and provider not in ("Ollama",):
            await log(f"⚠️  No API key found for {provider}. Set it in Settings.")

        profile = LLMProfile(
            provider=actual_provider,
            model=model,
            temperature=0.2,
            base_url=base_url,
            kwargs=profile_kwargs,
        )

        max_steps = int(cfg("max_steps", 15))

        agent_cfg = AgentConfig(
            max_steps=max_steps,
            reasoning=enable_reasoning,
            fast_agent=FastAgentConfig(vision=enable_vision),
            manager=ManagerConfig(vision=enable_vision),
            executor=ExecutorConfig(vision=enable_vision),
        )

        config = DroidConfig(
            agent=agent_cfg,
            device=DeviceConfig(),  # serial unused; we inject driver directly
            llm_profiles={
                "manager": profile,
                "executor": profile,
                "fast_agent": profile,
                "app_opener": profile,
                "structured_output": profile,
            },
        )

        # ------------------------------------------------------------------ #
        # Create WebSocketDevice and inject into DroidAgent
        # ------------------------------------------------------------------ #
        driver = WebSocketDevice(conn)

        await log("✅ Starting agent...")

        # Capture agent logs via callback
        def _cb(msg: str):
            asyncio.get_event_loop().call_soon_threadsafe(log_queue.put_nowait, msg)

        agent = DroidAgent(
            goal=goal,
            config=config,
            driver=driver,
        )

        result = await agent.run()

        await log("✅ Task completed")
        return {
            "success": bool(result.success),
            "reason": result.reason or "",
            "steps": result.steps or 0,
        }

    except Exception as e:
        msg = str(e)
        await log(f"❌ Error: {msg}")
        logger.exception("Task %s failed", task_id)
        return {"success": False, "reason": msg, "steps": 0}
