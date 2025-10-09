"""
FastAPI server for DroidRun web interface.

This module provides REST API and SSE endpoints for controlling DroidAgent
from a web frontend.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from droidrun.backend.agent_runner import get_agent_runner
from droidrun.backend.models import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStatusResponse,
    AgentStopResponse,
    ErrorResponse,
    SessionListResponse,
    SessionStatus,
)
from droidrun.backend.session_manager import get_session_manager
from droidrun.backend.websocket import websocket_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("droidrun.backend")

# Create FastAPI app
app = FastAPI(
    title="DroidRun Backend API",
    description="REST API and SSE for controlling DroidAgent",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get singleton instances
agent_runner = get_agent_runner()
session_manager = get_session_manager()


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Agent Management Endpoints
# =============================================================================


@app.post("/api/agent/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest):
    """
    Start a new agent execution.

    Args:
        request: Agent configuration

    Returns:
        AgentRunResponse with session_id and status
    """
    try:
        # Create session
        session = await session_manager.create_session(request)

        # Start agent execution in background
        await agent_runner.start_agent(session.session_id, request)

        logger.info(f"Started agent for session {session.session_id}")

        return AgentRunResponse(
            session_id=session.session_id,
            status=SessionStatus.RUNNING,
            message="Agent execution started",
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting agent: {str(e)}")


@app.get("/api/agent/status/{session_id}", response_model=AgentStatusResponse)
async def get_agent_status(session_id: str):
    """
    Get status of an agent execution.

    Args:
        session_id: Session identifier

    Returns:
        AgentStatusResponse with session details
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    is_running = await agent_runner.is_running(session_id)

    return AgentStatusResponse(
        session=session,
        current_step=None,  # Could be tracked in session if needed
        total_steps=None,
    )


@app.post("/api/agent/stop/{session_id}", response_model=AgentStopResponse)
async def stop_agent(session_id: str):
    """
    Stop a running agent execution.

    Args:
        session_id: Session identifier

    Returns:
        AgentStopResponse with stop status
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.status not in (SessionStatus.PENDING, SessionStatus.RUNNING):
        return AgentStopResponse(
            session_id=session_id,
            status=session.status,
            message=f"Agent is not running (status: {session.status.value})",
        )

    # Stop the agent
    stopped = await agent_runner.stop_agent(session_id)

    if stopped:
        return AgentStopResponse(
            session_id=session_id,
            status=SessionStatus.STOPPED,
            message="Agent execution stopped",
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to stop agent")


@app.get("/api/agent/sessions", response_model=SessionListResponse)
async def list_sessions(
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(10, ge=1, le=100, description="Maximum sessions to return"),
):
    """
    List agent sessions.

    Args:
        status: Optional status filter
        limit: Maximum number of sessions

    Returns:
        SessionListResponse with list of sessions
    """
    sessions = await session_manager.list_sessions(status_filter=status, limit=limit)

    return SessionListResponse(sessions=sessions, total=len(sessions))


@app.delete("/api/agent/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    # Stop agent if running
    await agent_runner.stop_agent(session_id)

    # Cleanup session resources
    await agent_runner.cleanup_session(session_id)

    # Delete from session manager
    deleted = await session_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {"message": f"Session {session_id} deleted", "session_id": session_id}


# =============================================================================
# SSE Streaming Endpoint
# =============================================================================


@app.get("/api/agent/stream/{session_id}")
async def stream_events(session_id: str):
    """
    Stream agent events via Server-Sent Events (SSE).

    Args:
        session_id: Session identifier

    Returns:
        StreamingResponse with SSE events
    """
    # Check if session exists
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in agent_runner.stream_events(session_id):
                # Format as SSE
                event_data = event.model_dump_json()
                yield f"event: {event.event_type.value}\n"
                yield f"data: {event_data}\n\n"

        except ValueError as e:
            # Session not found or no event queue
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"

        except Exception as e:
            logger.error(f"Error streaming events for session {session_id}: {e}", exc_info=True)
            error_data = json.dumps({"error": f"Streaming error: {str(e)}"})
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/api/agent/ws/{connection_id}")
async def websocket_handler(websocket: WebSocket, connection_id: str):
    """
    WebSocket endpoint for bidirectional communication.

    Args:
        websocket: WebSocket connection
        connection_id: Unique connection identifier

    Usage:
        const ws = new WebSocket('ws://localhost:8000/api/agent/ws/my-connection-id');

        // Subscribe to a session
        ws.send(JSON.stringify({
            type: 'subscribe',
            session_id: 'session-uuid-here'
        }));

        // Receive events
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('Event:', message);
        };
    """
    await websocket_endpoint(websocket, connection_id)


# =============================================================================
# Admin/Maintenance Endpoints
# =============================================================================


@app.post("/api/admin/cleanup")
async def cleanup_old_sessions(max_age_hours: int = Query(24, ge=1, le=168)):
    """
    Cleanup old completed sessions.

    Args:
        max_age_hours: Maximum age in hours

    Returns:
        Cleanup statistics
    """
    deleted_count = await session_manager.cleanup_old_sessions(max_age_hours)

    return {
        "message": f"Cleaned up {deleted_count} old sessions",
        "deleted_count": deleted_count,
        "max_age_hours": max_age_hours,
    }


@app.get("/api/admin/stats")
async def get_stats():
    """
    Get backend statistics.

    Returns:
        Statistics about sessions and agents
    """
    total_sessions = await session_manager.get_session_count()
    running_sessions = await session_manager.get_session_count(SessionStatus.RUNNING)
    completed_sessions = await session_manager.get_session_count(SessionStatus.COMPLETED)
    failed_sessions = await session_manager.get_session_count(SessionStatus.FAILED)

    return {
        "total_sessions": total_sessions,
        "running_sessions": running_sessions,
        "completed_sessions": completed_sessions,
        "failed_sessions": failed_sessions,
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    """Handle Pydantic validation errors."""
    return ErrorResponse(
        error="Validation error", detail=str(exc)
    ).model_dump()


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return ErrorResponse(error=exc.detail, detail=None).model_dump()


# =============================================================================
# Startup/Shutdown Events
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize backend on startup."""
    logger.info("DroidRun backend starting up...")
    logger.info("Backend API ready at http://localhost:8000")
    logger.info("API docs available at http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("DroidRun backend shutting down...")
    # Could add cleanup logic here if needed


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "droidrun.backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
