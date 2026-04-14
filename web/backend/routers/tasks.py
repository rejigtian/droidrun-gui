"""
/api/tasks  — create tasks, list history, stream logs via SSE
"""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from db.database import AsyncSessionLocal, get_db_session
from db.models import Task, TaskLog
from core.task_runner import run_task

router = APIRouter(prefix="/api")

# task_id → asyncio.Queue for SSE streaming
_log_queues: dict[str, asyncio.Queue] = {}


# ---- schemas ----------------------------------------------------------------

class TaskCreate(BaseModel):
    goal: str
    device_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    enable_vision: bool = False
    enable_reasoning: bool = False


class TaskOut(BaseModel):
    id: str
    goal: str
    device_id: Optional[str]
    status: str
    success: Optional[bool]
    reason: str
    steps: int
    provider: str
    model: str
    created_at: str
    finished_at: Optional[str]


class TaskLogOut(BaseModel):
    id: int
    message: str
    created_at: str


# ---- helpers ----------------------------------------------------------------

def _task_to_out(t: Task) -> TaskOut:
    return TaskOut(
        id=t.id,
        goal=t.goal,
        device_id=t.device_id,
        status=t.status,
        success=bool(t.success) if t.success is not None else None,
        reason=t.reason or "",
        steps=t.steps or 0,
        provider=t.provider or "",
        model=t.model or "",
        created_at=t.created_at.isoformat() if t.created_at else "",
        finished_at=t.finished_at.isoformat() if t.finished_at else None,
    )


# ---- routes -----------------------------------------------------------------

@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate):
    """Launch a new task. Execution runs in a background asyncio task."""
    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _log_queues[task_id] = queue

    from core.settings_manager import get as cfg
    provider = body.provider or cfg("default_provider", "GoogleGenAI")
    model_map = {
        "GoogleGenAI": cfg("gemini_model", "gemini-2.0-flash"),
        "OpenAI": cfg("openai_model", "gpt-4o"),
        "Anthropic": cfg("anthropic_model", "claude-sonnet-4-6"),
        "DeepSeek": cfg("deepseek_model", "deepseek-chat"),
        "ZhipuAI": cfg("zhipu_model", "glm-4-plus"),
        "Ollama": cfg("ollama_model", "llama3.2"),
    }
    model = body.model or model_map.get(provider, "")

    # Create DB record
    async with get_db_session() as session:
        task = Task(
            id=task_id,
            device_id=body.device_id,
            goal=body.goal,
            status="running",
            provider=provider,
            model=model,
        )
        session.add(task)
        await session.commit()

    # Run in background
    asyncio.create_task(
        _execute_task(
            task_id=task_id,
            goal=body.goal,
            device_id=body.device_id,
            queue=queue,
            provider=provider,
            model=model,
            enable_vision=body.enable_vision,
            enable_reasoning=body.enable_reasoning,
        )
    )

    async with get_db_session() as session:
        row = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one()
        return _task_to_out(row)


async def _execute_task(
    task_id, goal, device_id, queue,
    provider, model, enable_vision, enable_reasoning
):
    """Background coroutine: run agent, then finalize DB record."""
    result = await run_task(
        task_id=task_id,
        goal=goal,
        device_id=device_id,
        log_queue=queue,
        provider_override=provider,
        model_override=model,
        enable_vision=enable_vision,
        enable_reasoning=enable_reasoning,
    )

    # Finalize task
    async with AsyncSessionLocal() as session:
        row = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if row:
            row.status = "done" if result["success"] else "error"
            row.success = result["success"]
            row.reason = result["reason"]
            row.steps = result["steps"]
            row.finished_at = datetime.utcnow()
            await session.commit()

    # Signal SSE stream to close
    await queue.put(None)


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(limit: int = 50, offset: int = 0):
    async with get_db_session() as session:
        rows = (
            await session.execute(
                select(Task)
                .order_by(Task.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
    return [_task_to_out(t) for t in rows]


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: str):
    async with get_db_session() as session:
        row = (
            await session.execute(select(Task).where(Task.id == task_id))
        ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_out(row)


@router.get("/tasks/{task_id}/logs", response_model=list[TaskLogOut])
async def get_task_logs(task_id: str):
    """Return all stored log lines for a completed task."""
    async with get_db_session() as session:
        logs = (
            await session.execute(
                select(TaskLog)
                .where(TaskLog.task_id == task_id)
                .order_by(TaskLog.id)
            )
        ).scalars().all()
    return [
        TaskLogOut(
            id=l.id,
            message=l.message,
            created_at=l.created_at.isoformat() if l.created_at else "",
        )
        for l in logs
    ]


@router.get("/tasks/{task_id}/stream")
async def stream_task_logs(task_id: str):
    """
    Server-Sent Events stream of live log lines.
    The stream closes when the task finishes (sentinel None in queue).
    """
    queue = _log_queues.get(task_id)

    if queue is None:
        # Task already finished — replay stored logs then close
        async def _replay():
            async with get_db_session() as session:
                logs = (
                    await session.execute(
                        select(TaskLog)
                        .where(TaskLog.task_id == task_id)
                        .order_by(TaskLog.id)
                    )
                ).scalars().all()
            for l in logs:
                yield f"data: {l.message}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_replay(), media_type="text/event-stream")

    async def _stream() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    # Keep-alive
                    yield ": ping\n\n"
                    continue
                if msg is None:
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {msg}\n\n"
        finally:
            _log_queues.pop(task_id, None)

    return StreamingResponse(_stream(), media_type="text/event-stream")
