"""
DroidRun WebGUI — FastAPI backend entry point
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.database import init_db
from ws.portal_ws import portal_websocket_endpoint
from routers.devices import router as devices_router
from routers.tasks import router as tasks_router
from routers.settings import router as settings_router
from core.settings_manager import get_all, _propagate_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise DB tables
    await init_db()
    # Propagate stored API keys to environment
    _propagate_env(get_all())
    logger.info("DroidRun WebGUI backend started")
    yield
    logger.info("DroidRun WebGUI backend stopped")


app = FastAPI(title="DroidRun WebGUI", version="1.0.0", lifespan=lifespan)

# CORS — allow the Vite dev server and any origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routers
app.include_router(devices_router)
app.include_router(tasks_router)
app.include_router(settings_router)


# WebSocket endpoint — Portal Android app connects here
@app.websocket("/v1/providers/join")
async def ws_portal(websocket: WebSocket):
    await portal_websocket_endpoint(websocket)


# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve built React frontend (production)
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
