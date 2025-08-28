from typing import Dict, Set

from fastapi import WebSocket


class SessionWebSocketManager:
    def __init__(self) -> None:
        self.session_to_clients: Dict[int, Set[WebSocket]] = {}

    async def connect(self, session_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.session_to_clients.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: int, websocket: WebSocket) -> None:
        clients = self.session_to_clients.get(session_id)
        if clients and websocket in clients:
            clients.remove(websocket)
        if clients is not None and len(clients) == 0:
            self.session_to_clients.pop(session_id, None)

    async def broadcast(self, session_id: int, message: dict) -> None:
        for ws in list(self.session_to_clients.get(session_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                # best-effort - clean up dead sockets
                self.disconnect(session_id, ws)


ws_manager = SessionWebSocketManager()


