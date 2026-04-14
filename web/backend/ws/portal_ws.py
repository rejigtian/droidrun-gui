"""
WebSocket endpoint that Portal Android app connects to (reverse connection).

Portal → Server: Bearer token auth, then sends JSON-RPC responses.
Server → Portal: JSON-RPC requests to control the device.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select, update

from db.database import AsyncSessionLocal
from db.models import Device

logger = logging.getLogger(__name__)

# Global registry: device_id → DeviceConnection
# Accessed by ws_device.py to send RPC calls
connected_devices: Dict[str, "DeviceConnection"] = {}


@dataclass
class DeviceConnection:
    ws: WebSocket
    device_id: str
    device_name: str
    token: str
    pending: Dict[str, asyncio.Future] = field(default_factory=dict)
    is_connected: bool = True


async def portal_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint at /v1/providers/join
    Mirrors the mobilerun.ai endpoint that Portal app already supports.
    """
    # Extract headers before accepting
    headers = dict(websocket.headers)
    authorization = headers.get("authorization", "")
    device_id = headers.get("x-device-id", "")
    device_name = headers.get("x-device-name", "Unknown Device")

    # Validate Bearer token
    if not authorization.startswith("Bearer "):
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized")
        return

    token = authorization.removeprefix("Bearer ").strip()

    # Look up device by token in DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Device).where(Device.token == token))
        device_row = result.scalar_one_or_none()

    if device_row is None:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Always key by DB id so list_devices() lookup works
    db_device_id = device_row.id
    await websocket.accept()

    conn = DeviceConnection(
        ws=websocket,
        device_id=db_device_id,
        device_name=device_name,
        token=token,
    )
    connected_devices[db_device_id] = conn

    # Update device status to online
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Device)
            .where(Device.token == token)
            .values(status="online", last_seen=datetime.utcnow(),
                    name=device_name or device_row.name)
        )
        await session.commit()

    logger.info("Device connected: %s (%s)", db_device_id, device_name)

    try:
        while True:
            raw = await websocket.receive_text()
            _handle_message(conn, raw)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("Portal WS error for %s: %s", db_device_id, e)
    finally:
        conn.is_connected = False
        connected_devices.pop(db_device_id, None)

        # Mark device offline
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Device)
                .where(Device.token == token)
                .values(status="offline", last_seen=datetime.utcnow())
            )
            await session.commit()

        # Resolve any still-pending futures with an error
        for fut in conn.pending.values():
            if not fut.done():
                fut.set_exception(RuntimeError("Device disconnected"))
        conn.pending.clear()

        logger.info("Device disconnected: %s", db_device_id)


def _handle_message(conn: DeviceConnection, raw: str):
    """Route an incoming message to the appropriate pending Future."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Non-JSON message from %s: %.200s", conn.device_id, raw)
        return

    msg_id = str(msg.get("id", ""))
    if not msg_id:
        return

    future = conn.pending.pop(msg_id, None)
    if future is None or future.done():
        return

    if "result" in msg:
        future.set_result(msg["result"])
    elif "error" in msg:
        err = msg["error"]
        if isinstance(err, dict):
            err = err.get("message", str(err))
        future.set_exception(RuntimeError(str(err)))
    else:
        # Empty result (void call succeeded)
        future.set_result(None)


async def send_rpc(
    conn: DeviceConnection,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Any:
    """
    Send a JSON-RPC request to the Portal app and await the response.
    Raises TimeoutError or RuntimeError on failure.
    """
    import uuid

    call_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    conn.pending[call_id] = future

    payload = json.dumps({"id": call_id, "method": method, "params": params or {}})
    try:
        await conn.ws.send_text(payload)
    except Exception as e:
        conn.pending.pop(call_id, None)
        raise RuntimeError(f"Failed to send RPC '{method}': {e}") from e

    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        conn.pending.pop(call_id, None)
        raise TimeoutError(f"RPC '{method}' timed out after {timeout}s")
