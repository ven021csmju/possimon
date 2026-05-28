import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from fastapi import WebSocket, status
from core.logging_config import logger

class ConnectionManager:
    def __init__(self):
        # active_connections: { user_id: [WebSocket, ...] }
        # Supports multiple devices for the same user
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # reverse_lookup: { WebSocket: user_id }
        self.reverse_lookup: Dict[WebSocket, str] = {}
        # heartbeat_tasks: { WebSocket: Task }
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept connection and start heartbeat."""
        try:
            await websocket.accept()
            
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            self.active_connections[user_id].append(websocket)
            self.reverse_lookup[websocket] = user_id
            
            # Start heartbeat task for this connection
            self.heartbeat_tasks[websocket] = asyncio.create_task(
                self._heartbeat(websocket, user_id)
            )
            
            logger.info(f"WebSocket connected: user_id={user_id}. Total users: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error during WebSocket connection for user {user_id}: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    def disconnect(self, websocket: WebSocket):
        """Clean up connection and stop heartbeat."""
        user_id = self.reverse_lookup.get(websocket)
        if user_id:
            if websocket in self.active_connections.get(user_id, []):
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            del self.reverse_lookup[websocket]
            
            # Cancel heartbeat task
            if websocket in self.heartbeat_tasks:
                self.heartbeat_tasks[websocket].cancel()
                del self.heartbeat_tasks[websocket]
                
            logger.info(f"WebSocket disconnected: user_id={user_id}. Remaining users: {len(self.active_connections)}")

    async def _heartbeat(self, websocket: WebSocket, user_id: str):
        """
        Send periodic ping to keep connection alive on Render/Cloudflare.
        Render idle timeout is usually 30-60 seconds.
        """
        try:
            while True:
                await asyncio.sleep(30)  # Ping every 30 seconds
                try:
                    # We use a custom ping message instead of WS ping frame 
                    # as some proxies handle frames differently than text pings
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                except Exception:
                    logger.warning(f"Heartbeat failed for user {user_id}, disconnecting.")
                    self.disconnect(websocket)
                    break
        except asyncio.CancelledError:
            pass

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections of a specific user."""
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    # Don't disconnect here, let the receive loop or heartbeat handle it

    async def broadcast(self, message: dict):
        """Send message to all active connections."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")

manager = ConnectionManager()
