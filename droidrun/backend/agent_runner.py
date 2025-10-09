"""
Agent runner for executing DroidAgent without modifying agent code.

This module wraps DroidAgent execution, manages lifecycle, and streams
events to the web interface.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

from adbutils import adb
from droidrun.backend.models import EventType

from droidrun.agent.context.personas import BIG_AGENT, DEFAULT
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.config_manager.config_manager import VisionConfig as DroidVisionConfig
from droidrun.tools import AdbTools, IOSTools

from datetime import datetime
from droidrun.backend.event_formatter import EventFormatter
from droidrun.backend.models import (
    AgentRunRequest,
    FormattedEvent,
    LLMConfig,
    SessionStatus,
)
from droidrun.backend.session_manager import get_session_manager

from droidrun.config_manager import config as droidrun_config

logger = logging.getLogger("droidrun.backend")


class AgentRunner:
    """
    Manages DroidAgent execution without modifying agent code.

    This class wraps DroidAgent, handles configuration from the frontend,
    and streams formatted events for web consumption.
    """

    def __init__(self):
        """Initialize the agent runner."""
        self._running_agents: dict[str, asyncio.Task] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}
        self.session_manager = get_session_manager()

    async def start_agent(self, session_id: str, config: AgentRunRequest) -> None:
        """
        Start agent execution in the background.

        Args:
            session_id: Session identifier
            config: Agent configuration from frontend
        """
        # Create event queue for this session
        self._event_queues[session_id] = asyncio.Queue()

        # Start agent execution as background task
        task = asyncio.create_task(self._run_agent(session_id, config))
        self._running_agents[session_id] = task

        logger.info(f"Started agent execution for session {session_id}")

    async def _run_agent(self, session_id: str, config: AgentRunRequest) -> None:
        """
        Internal method to run the agent.

        Args:
            session_id: Session identifier
            config: Agent configuration
        """
        event_queue = self._event_queues[session_id]
        formatter = EventFormatter(session_id)

        try:
            # Update session status to running
            await self.session_manager.update_session_status(session_id, SessionStatus.RUNNING)

            # Send status update
            await event_queue.put(formatter.format_status_update("Initializing agent..."))

            # ================================================================
            # Setup LLMs
            # ================================================================
            llms = await self._setup_llms(config, formatter, event_queue)

            # ================================================================
            # Setup device and tools
            # ================================================================
            await event_queue.put(formatter.format_status_update("Setting up device connection..."))
            tools = await self._setup_tools(config, llms)

            # ================================================================
            # Setup personas and excluded tools
            # ================================================================
            personas = [BIG_AGENT] if config.allow_drag else [DEFAULT]
            excluded_tools = [] if config.allow_drag else ["drag"]
            if config.excluded_tools:
                excluded_tools.extend(config.excluded_tools)

            # ================================================================
            # Setup vision config
            # ================================================================
            vision_config = self._setup_vision_config(config)

            # ================================================================
            # Create DroidAgent
            # ================================================================
            await event_queue.put(formatter.format_status_update("Creating DroidAgent..."))

            droid_agent = DroidAgent(
                goal=config.goal,
                llms=llms,
                vision=vision_config,
                tools=tools,
                personas=personas,
                excluded_tools=excluded_tools,
                max_steps=config.max_steps,
                timeout=config.timeout,
                reasoning=config.reasoning,
                enable_tracing=config.tracing,
                debug=config.debug,
                save_trajectories=config.save_trajectory.value,
            )

            # ================================================================
            # Run agent and stream events
            # ================================================================
            await event_queue.put(formatter.format_status_update("Starting agent execution..."))

            handler = droid_agent.run()

            # Stream events from agent
            async for event in handler.stream_events():
                # Format event for frontend
                formatted_event = formatter.format_event(event)
                if formatted_event:
                    await event_queue.put(formatted_event)

            # Wait for final result
            result = await handler

            # Update session status to completed
            success = result.get("success", False) if isinstance(result, dict) else False
            if success:
                await self.session_manager.update_session_status(
                    session_id, SessionStatus.COMPLETED
                )
            else:
                await self.session_manager.update_session_status(
                    session_id, SessionStatus.FAILED, error=str(result)
                )

            logger.info(f"Agent execution completed for session {session_id}")

        except asyncio.CancelledError:
            # Agent was stopped
            await self.session_manager.update_session_status(session_id, SessionStatus.STOPPED)
            await event_queue.put(
                formatter.format_status_update("Agent execution stopped by user")
            )
            logger.info(f"Agent execution stopped for session {session_id}")

        except Exception as e:
            # Agent execution failed
            error_msg = str(e)
            logger.error(f"Agent execution failed for session {session_id}: {error_msg}", exc_info=True)
            await self.session_manager.update_session_status(
                session_id, SessionStatus.FAILED, error=error_msg
            )
            error_event = FormattedEvent(
                event_type=EventType.ERROR,
                session_id=session_id,
                data={"error": error_msg, "message": f"Agent execution failed: {error_msg}"},
            )
            await event_queue.put(error_event)

        finally:
            # Cleanup
            if session_id in self._running_agents:
                del self._running_agents[session_id]

    async def stream_events(self, session_id: str) -> AsyncIterator[FormattedEvent]:
        """
        Stream formatted events for a session.

        Args:
            session_id: Session identifier

        Yields:
            FormattedEvent objects
        """
        event_queue = self._event_queues.get(session_id)
        if not event_queue:
            raise ValueError(f"No event queue found for session {session_id}")

        while True:
            try:
                # Wait for next event with timeout
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                yield event

                # Check if agent is still running
                if session_id not in self._running_agents:
                    # Agent finished, drain remaining events
                    while not event_queue.empty():
                        try:
                            event = event_queue.get_nowait()
                            yield event
                        except asyncio.QueueEmpty:
                            break
                    break

            except asyncio.TimeoutError:
                # Send heartbeat/keep-alive

                heartbeat = FormattedEvent(
                    event_type=EventType.STATUS,
                    session_id=session_id,
                    data={"message": "heartbeat"},
                    timestamp=datetime.now(),
                )
                yield heartbeat

    async def stop_agent(self, session_id: str) -> bool:
        """
        Stop a running agent.

        Args:
            session_id: Session identifier

        Returns:
            True if stopped, False if not running
        """
        task = self._running_agents.get(session_id)
        if not task:
            return False

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        logger.info(f"Stopped agent for session {session_id}")
        return True

    async def is_running(self, session_id: str) -> bool:
        """
        Check if an agent is running.

        Args:
            session_id: Session identifier

        Returns:
            True if running
        """
        return session_id in self._running_agents

    async def cleanup_session(self, session_id: str) -> None:
        """
        Cleanup session resources.

        Args:
            session_id: Session identifier
        """
        # Stop agent if running
        await self.stop_agent(session_id)

        # Remove event queue
        if session_id in self._event_queues:
            del self._event_queues[session_id]

    # =========================================================================
    # Configuration Helper Methods
    # =========================================================================

    async def _setup_llms(
        self, config: AgentRunRequest, formatter: EventFormatter, event_queue: asyncio.Queue
    ) -> dict:
        """Setup LLMs from configuration."""
        await event_queue.put(formatter.format_status_update("Loading LLMs..."))

        llms = {}

        # Check if using default LLM for all agents
        if config.llms and config.llms.default:
            default_llm = self._load_single_llm(config.llms.default)
            llms = {
                "manager": default_llm,
                "executor": default_llm,
                "codeact": default_llm,
                "text_manipulator": default_llm,
                "app_opener": default_llm,
            }
        elif config.llms:
            # Load per-agent LLMs
            if config.llms.manager:
                llms["manager"] = self._load_single_llm(config.llms.manager)
            if config.llms.executor:
                llms["executor"] = self._load_single_llm(config.llms.executor)
            if config.llms.codeact:
                llms["codeact"] = self._load_single_llm(config.llms.codeact)
            if config.llms.text_manipulator:
                llms["text_manipulator"] = self._load_single_llm(config.llms.text_manipulator)
            if config.llms.app_opener:
                llms["app_opener"] = self._load_single_llm(config.llms.app_opener)
        else:
            # Use default configuration from config.yaml

            profile_names = ["manager", "executor", "codeact", "text_manipulator", "app_opener"]
            llms = droidrun_config.load_all_llms(profile_names=profile_names)

        return llms

    def _load_single_llm(self, llm_config: LLMConfig):
        """Load a single LLM from configuration."""
        kwargs = {
            "temperature": llm_config.temperature,
            **llm_config.additional_kwargs,
        }

        if llm_config.base_url:
            kwargs["base_url"] = llm_config.base_url
        if llm_config.api_base:
            kwargs["api_base"] = llm_config.api_base

        return load_llm(
            provider_name=llm_config.provider,
            model=llm_config.model,
            **kwargs,
        )

    async def _setup_tools(self, config: AgentRunRequest, llms: dict):
        """Setup tools (ADB or iOS)."""
        if config.ios:
            if not config.device:
                raise ValueError("iOS device URL must be specified via device parameter")
            return IOSTools(url=config.device)

        # Android/ADB tools
        device_serial = config.device

        if not device_serial:
            # Auto-detect device
            devices = adb.list()
            if not devices:
                raise ValueError("No connected devices found")
            device_serial = devices[0].serial
            logger.info(f"Auto-detected device: {device_serial}")

        return AdbTools(
            serial=device_serial,
            use_tcp=config.use_tcp,
            app_opener_llm=llms.get("app_opener"),
            text_manipulator_llm=llms.get("text_manipulator"),
        )

    def _setup_vision_config(self, config: AgentRunRequest) -> DroidVisionConfig:
        """Setup vision configuration."""
        if config.vision:
            return DroidVisionConfig(
                manager=config.vision.manager,
                executor=config.vision.executor,
                codeact=config.vision.codeact,
            )

        # Use default from config

        return droidrun_config.agent.vision


# Global agent runner instance
_agent_runner: Optional[AgentRunner] = None


def get_agent_runner() -> AgentRunner:
    """
    Get the global agent runner instance.

    Returns:
        AgentRunner singleton
    """
    global _agent_runner
    if _agent_runner is None:
        _agent_runner = AgentRunner()
    return _agent_runner
