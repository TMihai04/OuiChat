# websocket manager class and singleton

from .logger import logger

from collections import defaultdict
from fastapi import WebSocket, WebSocketException, WebSocketDisconnect, status
from pydantic import BaseModel
from typing import Literal


class WebsocketManager:
    active_connections: defaultdict(list)

    def __init__(self):
        self.active_connections = defaultdict(list)

    async def connect(
        self,
        username: str,
        websocket: WebSocket
    ) -> None:
        """Accepts the incoming websocket connection and saves the instance for the given user."""
        await websocket.accept()
        self.active_connections[username].append(websocket)

        logger.debug(f"WSManager: Connected websocket - username: {username} - connections: {len(self.active_connections.get(username))}")
    
    async def notify(
        self,
        weboscket: WebSocket,
        payload: dict | type[BaseModel],
        mode: Literal["text", "binary"] = "binary"
    ) -> None:
        """Sends a json payload to the given websocket instance."""
        if isinstance(payload, BaseModel):
            payload = payload.model_dump()

        try:
            await weboscket.send_json(
                data=payload,
                mode=mode
            )
        except WebSocketDisconnect:
            pass
        
        logger.debug(f"WSManager: Notified websocket")

    async def notify_user(
        self,
        username: str,
        payload: dict | type[BaseModel],
        mode: Literal["text", "binary"] = "binary"
    ) -> None:
        """Sends a json payload to all the websockets registered under the given username if username."""        
        for ws in self.active_connections.get(username, []):
            await self.notify(ws, payload, mode)
    
    async def notify_all(
        self,
        payload: dict | type[BaseModel],
        mode: Literal["text", "binary"] = "binary"
    ) -> None:
        """Sends a json payload to all the websockets registered in the manager."""
        for usr in self.active_connections.keys():
            await self.notify_user(usr, payload, mode)
    
    async def disconnect(
        self,
        username: str,
        webscoket: WebSocket,
        code: int = status.WS_1000_NORMAL_CLOSURE,
        reason: str | None = None,
        close: bool = True,
    ) -> None:
        """Closes the given websocket instance and removes it from the username's list. Can throw an error if provided."""
        if close:
            try:
                await webscoket.close(code, reason)
            except WebSocketDisconnect:
                pass
    
        try:
            self.active_connections.get(username).remove(webscoket)
        except ValueError:
            pass

        logger.debug(f"WSManager: Disconnected websocket - username: {username} - connections: {len(self.active_connections.get(username))}")
    
    async def disconnect_user(
        self,
        username: str,
        code: int = status.WS_1000_NORMAL_CLOSURE,
        reason: str | None = None,
        close: bool = True,
    ) -> None:
        """Closes and removes all websockets registered under the given username. Can throw an error if provided."""
        for ws in self.active_connections.get(username, []):
            await self.disconnect(username, ws, code, reason, close)
    
    async def disconnect_all(
        self,
        code: int = status.WS_1000_NORMAL_CLOSURE,
        reason: str | None = None,
        close: bool = True
    ) -> None:
        """Closes and removes all websockets present in the connection pool. Can throw an error if provided."""
        for usr in self.active_connections.keys():
            await self.disconnect_user(usr, code, reason, close)


ws_manager = WebsocketManager()