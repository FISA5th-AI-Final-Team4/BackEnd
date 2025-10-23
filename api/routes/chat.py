from fastapi import (
    APIRouter, HTTPException,
    WebSocket, WebSocketDisconnect,
    Path, Body, Depends
)

import uuid

from schemas.chat import (
    PersonaListResponse,
    ChatSessionRequest, ChatSessionResponse,
    ChatMessage, ChatHistoryResponse,
)


def _load_dummy_personas():
    import json
    import os
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    DUMMY_DATA_DIR = os.path.join(CURRENT_DIR, "../../tests/data")
    with open(os.path.join(DUMMY_DATA_DIR, "personas.json"), "r", encoding="utf-8") as f:
        dummy_personas = json.load(f)

    with open(os.path.join(DUMMY_DATA_DIR, "chat_history.json"), "r", encoding="utf-8") as f:
        dummy_chat_history = json.load(f)

    return dummy_personas, dummy_chat_history

dummy_personas, dummy_chat_history = _load_dummy_personas()


router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/personas", response_model=PersonaListResponse)
async def get_personas():
    return dummy_personas

@router.post("/session", response_model=ChatSessionResponse)
async def create_session(req: ChatSessionRequest):
    # 요청 body에 persona_id가 없으면 422 에러 반환
    if not req.persona_id:
        raise HTTPException(status_code=422, detail="persona_id is required")
    
    # 웹소켓 연결 및 세션 ID 반환
    session_id = dummy_chat_history['session_id']
    
    return {"session_id": session_id}

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    chat_history = dummy_chat_history['history']

    return {"session_id": session_id, "history": chat_history}

@router.websocket("/ws/{session_id}")
async def websocket_chat(session_id: str, websocket: WebSocket):
    pass