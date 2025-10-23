from fastapi import (
    APIRouter, HTTPException,
    WebSocket, WebSocketDisconnect,
    Path, Body, Depends
)

import uuid

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/personas")
async def get_personas():
    return {"personas": []}

@router.post("/session")
async def create_session():
    return {"session_id": str(uuid.uuid4())}

@router.get("/history/{session_id}")
async def get_chat_history(session_id):
    return {"session_id": session_id, "history": []}

@router.websocket("/ws/{session_id}")
async def websocket_chat(session_id: str, websocket: WebSocket):
    await websocket.accept()
    pass