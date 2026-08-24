import json
import logging
from typing import Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # dict of device_id (UUID string) -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"Device {device_id} connected via WS")

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Device {device_id} disconnected from WS")

    def is_online(self, device_id: str) -> bool:
        return device_id in self.active_connections

    async def send_command(self, device_id: str, command: dict) -> bool:
        """Send a command to a device. Returns True if sent successfully."""
        if device_id in self.active_connections:
            try:
                await self.active_connections[device_id].send_text(json.dumps(command))
                return True
            except Exception as e:
                logger.error(f"Failed to send command to {device_id}: {e}")
                self.disconnect(device_id)
                return False
        return False

# Global instance
manager = ConnectionManager()
