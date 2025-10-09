"""
Pydantic models for DroidRun backend API.

These models define the request/response schemas for the web interface.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# LLM Configuration Models
# =============================================================================


class LLMConfig(BaseModel):
    """Configuration for a single LLM."""

    provider: str = Field(..., description="LLM provider (e.g., OpenAI, GoogleGenAI, Anthropic)")
    model: str = Field(..., description="Model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    base_url: Optional[str] = Field(default=None, description="Custom base URL for API")
    api_base: Optional[str] = Field(default=None, description="API base URL")
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)


class LLMConfigs(BaseModel):
    """
    LLM configurations for all agents.

    Can be a single LLM for all agents (use 'default' key) or per-agent configs.
    """

    manager: Optional[LLMConfig] = Field(default=None, description="Manager agent LLM")
    executor: Optional[LLMConfig] = Field(default=None, description="Executor agent LLM")
    codeact: Optional[LLMConfig] = Field(default=None, description="CodeAct agent LLM")
    text_manipulator: Optional[LLMConfig] = Field(default=None, description="Text manipulator LLM")
    app_opener: Optional[LLMConfig] = Field(default=None, description="App opener LLM")
    default: Optional[LLMConfig] = Field(default=None, description="Default LLM for all agents")


# =============================================================================
# Vision Configuration Models
# =============================================================================


class VisionConfig(BaseModel):
    """Vision configuration for agents."""

    manager: bool = Field(default=False, description="Enable vision for Manager")
    executor: bool = Field(default=False, description="Enable vision for Executor")
    codeact: bool = Field(default=False, description="Enable vision for CodeAct")


# =============================================================================
# Agent Run Request Models
# =============================================================================


class SaveTrajectoryLevel(str, Enum):
    """Trajectory saving level."""

    NONE = "none"
    STEP = "step"
    ACTION = "action"


class AgentRunRequest(BaseModel):
    """Request to start an agent execution."""

    goal: str = Field(..., description="The task/goal for the agent to achieve")
    device: Optional[str] = Field(default=None, description="Device serial or IP address")
    llms: Optional[LLMConfigs] = Field(default=None, description="LLM configurations")
    vision: Optional[VisionConfig] = Field(default=None, description="Vision settings per agent")
    reasoning: bool = Field(default=False, description="Enable Manager+Executor reasoning mode")
    max_steps: int = Field(default=15, ge=1, le=100, description="Maximum execution steps")
    timeout: int = Field(default=1000, ge=10, description="Timeout in seconds")
    debug: bool = Field(default=False, description="Enable debug logging")
    tracing: bool = Field(default=False, description="Enable Arize Phoenix tracing")
    save_trajectory: SaveTrajectoryLevel = Field(default=SaveTrajectoryLevel.NONE)
    use_tcp: bool = Field(default=False, description="Use TCP for device communication")
    allow_drag: bool = Field(default=False, description="Enable drag tool")
    ios: bool = Field(default=False, description="Target iOS device")
    excluded_tools: list[str] = Field(default_factory=list, description="Tools to exclude")


# =============================================================================
# Agent Session Models
# =============================================================================


class SessionStatus(str, Enum):
    """Status of an agent session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AgentSession(BaseModel):
    """Information about an agent execution session."""

    session_id: str = Field(..., description="Unique session identifier")
    goal: str = Field(..., description="Agent goal")
    status: SessionStatus = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Session creation time")
    started_at: Optional[datetime] = Field(default=None, description="Execution start time")
    completed_at: Optional[datetime] = Field(default=None, description="Completion time")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    config: AgentRunRequest = Field(..., description="Agent configuration")


# =============================================================================
# API Response Models
# =============================================================================


class AgentRunResponse(BaseModel):
    """Response when starting an agent."""

    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Response message")


class AgentStatusResponse(BaseModel):
    """Response for status query."""

    session: AgentSession = Field(..., description="Session information")
    current_step: Optional[int] = Field(default=None, description="Current step number")
    total_steps: Optional[int] = Field(default=None, description="Total steps executed")


class AgentStopResponse(BaseModel):
    """Response when stopping an agent."""

    session_id: str = Field(..., description="Session identifier")
    status: SessionStatus = Field(..., description="Final status")
    message: str = Field(..., description="Response message")


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[AgentSession] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")


# =============================================================================
# Event Models (for formatted events)
# =============================================================================


class EventType(str, Enum):
    """Types of events streamed to frontend."""

    # Workflow events
    START = "start"
    STOP = "stop"

    # Agent thinking/planning
    LLM_THINKING = "llm_thinking"
    MANAGER_PLAN = "manager_plan"
    EXECUTOR_ACTION = "executor_action"

    # Execution events
    CODE_EXECUTION = "code_execution"
    EXECUTION_RESULT = "execution_result"

    # UI state events
    SCREENSHOT = "screenshot"
    UI_STATE = "ui_state"

    # Memory events
    EPISODIC_MEMORY = "episodic_memory"

    # Completion events
    TASK_END = "task_end"
    FINALIZE = "finalize"

    # Status updates
    STATUS = "status"
    ERROR = "error"


class FormattedEvent(BaseModel):
    """Base model for formatted events sent to frontend."""

    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    data: dict[str, Any] = Field(..., description="Event-specific data")
    session_id: str = Field(..., description="Associated session ID")


# =============================================================================
# WebSocket Message Models
# =============================================================================


class WebSocketMessageType(str, Enum):
    """Types of WebSocket messages."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    EVENT = "event"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: WebSocketMessageType = Field(..., description="Message type")
    session_id: Optional[str] = Field(default=None, description="Session ID (for subscribe/event)")
    data: Optional[dict[str, Any]] = Field(default=None, description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now)
