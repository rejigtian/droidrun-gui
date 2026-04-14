"""
/api/devices  — list connected devices, manage tokens
/api/tokens   — generate device tokens
"""

import secrets
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select

from db.database import get_db_session
from db.models import Device
from ws.portal_ws import connected_devices

router = APIRouter(prefix="/api")


# ---- schemas ----------------------------------------------------------------

class TokenCreate(BaseModel):
    name: str = "My Device"


class TokenOut(BaseModel):
    id: str
    name: str
    token: str


class DeviceOut(BaseModel):
    id: str
    name: str
    serial: str
    model: str
    status: str
    last_seen: str | None


# ---- routes -----------------------------------------------------------------

@router.get("/devices", response_model=list[DeviceOut])
async def list_devices():
    """Return all registered devices with live status."""
    async with get_db_session() as session:
        rows = (await session.execute(select(Device))).scalars().all()

    result = []
    for d in rows:
        # Reflect live connection status
        if d.id in connected_devices and connected_devices[d.id].is_connected:
            status = "online"
        else:
            status = "offline"

        result.append(
            DeviceOut(
                id=d.id,
                name=d.name or d.id,
                serial=d.serial,
                model=d.model,
                status=status,
                last_seen=d.last_seen.isoformat() if d.last_seen else None,
            )
        )
    return result


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: str):
    """Remove a device token (disconnects it on next attempt)."""
    async with get_db_session() as session:
        result = await session.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        await session.execute(delete(Device).where(Device.id == device_id))
        await session.commit()


@router.post("/tokens", response_model=TokenOut, status_code=201)
async def create_token(body: TokenCreate):
    """Generate a new device token to be pasted into the Portal app."""
    device_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)

    async with get_db_session() as session:
        session.add(
            Device(
                id=device_id,
                token=token,
                name=body.name,
                status="offline",
            )
        )
        await session.commit()

    return TokenOut(id=device_id, name=body.name, token=token)
