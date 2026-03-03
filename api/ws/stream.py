__pattern__ = "EventDriven"

import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

router = APIRouter()


@router.websocket("/ws/{problem_uuid}")
async def websocket_stream(websocket: WebSocket, problem_uuid: str):
    """Stream agent events to Hub via WebSocket. Reconnect with exponential backoff."""
    await websocket.accept()
    try:
        # TODO Phase 3: subscribe to Redis pub/sub channel oak:stream:{problem_uuid}
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
