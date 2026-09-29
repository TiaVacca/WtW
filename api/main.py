# api/main.py
import asyncio
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from collector.base import Collector, NetworkObservation
from collector.passive import PassiveCollector
from storage import db

app = FastAPI(title="Wardriver API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager ---
class WSManager:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.remove(ws)

ws_manager = WSManager()

# --- Collector ---
collector: PassiveCollector | None = None


async def pipeline_loop(collector: Collector):
    """Loop that reads from the collector, enriches, saves, and broadcasts observations."""
    async for obs in collector.observations():
        db.upsert(obs)
        await ws_manager.broadcast({"type": "observation", "data": obs.to_dict()})


# --- Lifespan ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global collector
    db.init_db()
    collector = PassiveCollector(iface="wlan0mon")
    await collector.start()
    task = asyncio.create_task(pipeline_loop(collector))
    yield
    await collector.stop()
    task.cancel()

app = FastAPI(title="Wardriver API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes ---
@app.get("/api/networks")
async def get_networks():
    return db.get_all_networks()


@app.get("/api/stats")
async def get_stats():
    return db.get_stats()


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # keep connection alive; the pipeline pushes the data
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# --- Endpoint for Active Mode (placeholder) ---
@app.post("/api/cmd/deauth")
async def cmd_deauth(payload: dict):
    """
    Placeholder for the active mode.
    When ActiveDeauthCollector is implemented,

    this endpoint will be used.
    """
    return {"status": "not_implemented", "detail": "Active mode coming soon"}  
 