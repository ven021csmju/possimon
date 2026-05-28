import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from auth.jwt import decode_token
from core.logging_config import logger
from .manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(None)
):
    """
    WebSocket endpoint with JWT authentication.
    Path: /ws?token=JWT_TOKEN
    """
    if not token:
        logger.warning("WebSocket connection attempt without token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify JWT
    payload = decode_token(token, expected_type="access")
    if not payload:
        logger.warning("WebSocket connection attempt with invalid or expired token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Extract user identity (sub is usually user_id)
    user_id = str(payload.get("sub"))
    if not user_id:
        logger.warning("WebSocket token missing 'sub' claim.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept connection and manage it
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Maintain connection and listen for messages if needed
            # We mostly use it for server-to-client notifications
            data = await websocket.receive_text()
            
            # Handle client-side pong or other messages
            try:
                message = json.loads(data)
                if message.get("type") == "pong":
                    logger.debug(f"Received pong from user {user_id}")
            except Exception:
                pass # Not a JSON message, or not a pong

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"User {user_id} disconnected normally.")
    except Exception as e:
        manager.disconnect(websocket)
        logger.error(f"Unexpected WebSocket error for user {user_id}: {e}")
