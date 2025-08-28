import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.websocket_manager import ws_manager


router = APIRouter()


@router.websocket("/ws/streams/{session_id}")
async def ws_stream(session_id: int, websocket: WebSocket):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if isinstance(msg, dict) and msg.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "nonce": msg.get("nonce"),
                    "server_time": int(time.time() * 1000),
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


