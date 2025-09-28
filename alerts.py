#!/usr/bin/env python3
from typing import List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

class AlertManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, message: dict):
        stale = []
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)

# Singleton instance to import across modules
alert_manager = AlertManager()

# Store reference to the main asyncio event loop used by FastAPI/Uvicorn
_event_loop: Optional[asyncio.AbstractEventLoop] = None

def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _event_loop
    _event_loop = loop

def broadcast_from_thread(message: dict):
    """Schedule a broadcast safely from non-async contexts/threads.
    Requires that set_event_loop() has been called during FastAPI startup.
    """
    if _event_loop and _event_loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(alert_manager.broadcast(message), _event_loop)
        except Exception:
            pass
