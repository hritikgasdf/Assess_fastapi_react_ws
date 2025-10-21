from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User
from app.auth import decode_token
from app.websocket import manager
from app.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    try:
        # Decode token first (no DB access needed)
        token_data = decode_token(token)
        
        # Create async session for user lookup
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).filter(User.email == token_data.email))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"WebSocket connection rejected: User not found for email {token_data.email}")
                await websocket.close(code=1008)
                return
            
            user_id = user.id
        
        # Connect WebSocket after DB session is closed
        await manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected for user_id: {user_id}")
        
        try:
            while True:
                data = await websocket.receive_text()
                # WebSocket is now fully async and non-blocking
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket disconnected for user_id: {user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=1008)
