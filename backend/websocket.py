"""
WebSocket support for DroidRun backend.

This module provides WebSocket endpoints as an alternative to SSE,
enabling bidirectional communication with the frontend.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from .agent_runner import get_agent_runner
from .models import WebSocketMessage, WebSocketMessageType
from .session_manager import get_session_manager

logger = logging.getLogger("droidrun.backend")


class WebSocketManager:
    """
    Manages WebSocket connections and event streaming.

    This class handles multiple WebSocket connections, allowing clients
    to subscribe to one or more agent sessions.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: dict[str, WebSocket] = {}  # connection_id -> websocket
        self.subscriptions: dict[str, set[str]] = {}  # connection_id -> set of session_ids
        self.agent_runner = get_agent_runner()
        self.session_manager = get_session_manager()

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """
        Accept a WebSocket connection.

        Args:
            websocket: WebSocket connection
            connection_id: Unique connection identifier
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        logger.info(f"WebSocket connection established: {connection_id}")

    async def disconnect(self, connection_id: str) -> None:
        """
        Handle WebSocket disconnection.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        logger.info(f"WebSocket connection closed: {connection_id}")

    async def subscribe(self, connection_id: str, session_id: str) -> bool:
        """
        Subscribe a connection to a session.

        Args:
            connection_id: Connection identifier
            session_id: Session to subscribe to

        Returns:
            True if subscribed successfully
        """
        # Check if session exists
        session = await self.session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Subscription failed: session {session_id} not found")
            return False

        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = set()

        self.subscriptions[connection_id].add(session_id)
        logger.info(f"Connection {connection_id} subscribed to session {session_id}")

        # Start streaming events for this subscription
        asyncio.create_task(self._stream_session_events(connection_id, session_id))

        return True

    async def unsubscribe(self, connection_id: str, session_id: str) -> None:
        """
        Unsubscribe a connection from a session.

        Args:
            connection_id: Connection identifier
            session_id: Session to unsubscribe from
        """
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].discard(session_id)
            logger.info(f"Connection {connection_id} unsubscribed from session {session_id}")

    async def send_message(
        self, connection_id: str, message: WebSocketMessage
    ) -> None:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Connection identifier
            message: Message to send
        """
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_json(message.model_dump())
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self.disconnect(connection_id)

    async def _stream_session_events(self, connection_id: str, session_id: str) -> None:
        """
        Stream events from a session to a WebSocket connection.

        Args:
            connection_id: Connection identifier
            session_id: Session identifier
        """
        try:
            async for event in self.agent_runner.stream_events(session_id):
                # Check if still subscribed
                if (
                    connection_id not in self.subscriptions
                    or session_id not in self.subscriptions[connection_id]
                ):
                    logger.info(
                        f"Stopping stream: {connection_id} unsubscribed from {session_id}"
                    )
                    break

                # Send event to WebSocket
                message = WebSocketMessage(
                    type=WebSocketMessageType.EVENT,
                    session_id=session_id,
                    data=event.model_dump(),
                )
                await self.send_message(connection_id, message)

        except ValueError as e:
            # Session not found or no event queue
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                session_id=session_id,
                data={"error": str(e)},
            )
            await self.send_message(connection_id, error_message)

        except Exception as e:
            logger.error(
                f"Error streaming events to {connection_id} for session {session_id}: {e}",
                exc_info=True,
            )
            error_message = WebSocketMessage(
                type=WebSocketMessageType.ERROR,
                session_id=session_id,
                data={"error": f"Streaming error: {str(e)}"},
            )
            await self.send_message(connection_id, error_message)

    async def handle_message(
        self, connection_id: str, message_data: dict
    ) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            connection_id: Connection identifier
            message_data: Message data
        """
        try:
            message = WebSocketMessage(**message_data)

            if message.type == WebSocketMessageType.SUBSCRIBE:
                # Subscribe to session
                if not message.session_id:
                    await self.send_message(
                        connection_id,
                        WebSocketMessage(
                            type=WebSocketMessageType.ERROR,
                            data={"error": "session_id required for subscribe"},
                        ),
                    )
                    return

                success = await self.subscribe(connection_id, message.session_id)
                if success:
                    await self.send_message(
                        connection_id,
                        WebSocketMessage(
                            type=WebSocketMessageType.EVENT,
                            session_id=message.session_id,
                            data={
                                "message": f"Subscribed to session {message.session_id}"
                            },
                        ),
                    )
                else:
                    await self.send_message(
                        connection_id,
                        WebSocketMessage(
                            type=WebSocketMessageType.ERROR,
                            session_id=message.session_id,
                            data={"error": f"Session {message.session_id} not found"},
                        ),
                    )

            elif message.type == WebSocketMessageType.UNSUBSCRIBE:
                # Unsubscribe from session
                if message.session_id:
                    await self.unsubscribe(connection_id, message.session_id)
                    await self.send_message(
                        connection_id,
                        WebSocketMessage(
                            type=WebSocketMessageType.EVENT,
                            session_id=message.session_id,
                            data={
                                "message": f"Unsubscribed from session {message.session_id}"
                            },
                        ),
                    )

            elif message.type == WebSocketMessageType.PING:
                # Respond with pong
                await self.send_message(
                    connection_id,
                    WebSocketMessage(type=WebSocketMessageType.PONG),
                )

            else:
                logger.warning(f"Unknown message type: {message.type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await self.send_message(
                connection_id,
                WebSocketMessage(
                    type=WebSocketMessageType.ERROR,
                    data={"error": f"Message handling error: {str(e)}"},
                ),
            )


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.

    Returns:
        WebSocketManager singleton
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager


# =============================================================================
# WebSocket Endpoint Handler
# =============================================================================


async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """
    WebSocket endpoint handler.

    Args:
        websocket: WebSocket connection
        connection_id: Unique connection identifier
    """
    manager = get_websocket_manager()
    await manager.connect(websocket, connection_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            await manager.handle_message(connection_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
        await manager.disconnect(connection_id)

    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
        await manager.disconnect(connection_id)
