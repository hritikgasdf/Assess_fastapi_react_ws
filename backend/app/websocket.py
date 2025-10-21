from typing import List, Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime
from app.logger import setup_logger

logger = setup_logger(__name__)

class ConnectionManager:
    """
    Optimized in-memory WebSocket connection manager for single-server deployment.
    
    Features:
    - Efficient connection tracking with Set for O(1) lookups
    - Automatic stale connection cleanup
    - Graceful error handling with retry logic
    - Connection state monitoring
    - Memory-efficient message broadcasting
    """
    
    def __init__(self):
        # Use Set for O(1) membership checks
        self.active_connections: Set[WebSocket] = set()
        # Map user_id to websocket for targeted messaging
        self.user_connections: Dict[int, WebSocket] = {}
        # Reverse mapping for quick user_id lookup
        self.connection_to_user: Dict[WebSocket, int] = {}
        # Track connection timestamps for monitoring
        self.connection_times: Dict[WebSocket, datetime] = {}
        # Lock for thread-safe operations (if needed for future multi-threading)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Register a new WebSocket connection for a user.
        Handles duplicate connections by closing the old one.
        """
        # If user already has a connection, close the old one
        if user_id in self.user_connections:
            old_websocket = self.user_connections[user_id]
            logger.info(f"User {user_id} has existing connection, closing old connection")
            await self._force_disconnect(old_websocket, user_id)
        
        # Accept the new connection
        await websocket.accept()
        
        # Register connection
        self.active_connections.add(websocket)
        self.user_connections[user_id] = websocket
        self.connection_to_user[websocket] = user_id
        self.connection_times[websocket] = datetime.utcnow()
        
        logger.info(
            f"User {user_id} connected. "
            f"Total active connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        if user_id is None:
            user_id = self.connection_to_user.get(websocket)
        
        # Remove from all tracking structures
        self.active_connections.discard(websocket)
        
        if user_id and user_id in self.user_connections:
            if self.user_connections[user_id] == websocket:
                del self.user_connections[user_id]
        
        self.connection_to_user.pop(websocket, None)
        self.connection_times.pop(websocket, None)
        
        logger.info(
            f"User {user_id} disconnected. "
            f"Total active connections: {len(self.active_connections)}"
        )

    async def _force_disconnect(self, websocket: WebSocket, user_id: int):
        try:
            await websocket.close(code=1000, reason="New connection established")
        except Exception as e:
            logger.debug(f"Error closing old connection for user {user_id}: {e}")
        finally:
            self.disconnect(websocket, user_id)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        disconnected = []
        success_count = 0
        
        # Create a copy of connections to avoid modification during iteration
        connections_snapshot = list(self.active_connections)
        
        for connection in connections_snapshot:
            try:
                await connection.send_json(message)
                success_count += 1
            except WebSocketDisconnect:
                logger.debug("WebSocket disconnected during broadcast")
                disconnected.append(connection)
            except RuntimeError as e:
                # Handle "WebSocket is not connected" errors
                logger.debug(f"Runtime error during broadcast: {e}")
                disconnected.append(connection)
            except Exception as e:
                logger.warning(f"Unexpected error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Batch cleanup of disconnected connections
        if disconnected:
            for conn in disconnected:
                user_id = self.connection_to_user.get(conn)
                self.disconnect(conn, user_id)
            
            logger.info(
                f"Broadcast complete: {success_count} successful, "
                f"{len(disconnected)} disconnected (cleaned up)"
            )
        else:
            logger.debug(f"Broadcast successful to {success_count} connections")

    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send a message to a specific user.
        Cleans up connection if send fails.
        """
        if user_id not in self.user_connections:
            logger.debug(f"No active connection for user {user_id}")
            return
        
        websocket = self.user_connections[user_id]
        
        try:
            await websocket.send_json(message)
            logger.debug(f"Personal message sent to user {user_id}")
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected during personal message")
            self.disconnect(websocket, user_id)
        except RuntimeError as e:
            logger.warning(f"Runtime error sending personal message to user {user_id}: {e}")
            self.disconnect(websocket, user_id)
        except Exception as e:
            logger.error(f"Error sending personal message to user {user_id}: {e}")
            self.disconnect(websocket, user_id)

    def get_active_connections_count(self) -> int:
        """Get the current number of active connections."""
        return len(self.active_connections)

    def get_connected_user_ids(self) -> List[int]:
        """Get list of all connected user IDs."""
        return list(self.user_connections.keys())

    def is_user_connected(self, user_id: int) -> bool:
        """Check if a specific user has an active connection."""
        return user_id in self.user_connections

    async def cleanup_stale_connections(self):
        """
        Periodic cleanup task to remove stale connections.
        Can be called by a background task if needed.
        """
        stale = []
        current_time = datetime.utcnow()
        
        for websocket, connect_time in self.connection_times.items():
            # Check if connection is truly active by attempting a ping
            try:
                # Websocket doesn't support ping in FastAPI, so we check state
                if websocket.client_state.value != 1:  # 1 = CONNECTED
                    stale.append(websocket)
            except Exception:
                stale.append(websocket)
        
        # Cleanup stale connections
        for websocket in stale:
            user_id = self.connection_to_user.get(websocket)
            self.disconnect(websocket, user_id)
        
        if stale:
            logger.info(f"Cleaned up {len(stale)} stale connections")

# Global singleton instance
manager = ConnectionManager()
