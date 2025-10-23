from fastapi import (
    APIRouter, HTTPException,
    WebSocket, WebSocketDisconnect,
    Path, Body, Depends
)

from uuid import UUID, uuid4
from typing import Dict

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

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}

    async def connect(self, session_id: UUID, websocket: WebSocket):
        """새로운 WebSocket 연결을 수락하고 관리 목록에 추가"""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: UUID):
        """WebSocket 연결을 관리 목록에서 제거"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: Dict[str, bool | str], session_id: UUID):
        """특정 세션(클라이언트)에게 JSON 메시지 전송"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
        # session_id 없는 경우 예외처리 필요

dummy_personas, dummy_chat_history = _load_dummy_personas()
manager = ConnectionManager()

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
    session_id = uuid4()
    
    return {"session_id": session_id}

@router.get("/history/{session_id}")
async def get_chat_history(session_id: UUID):
    chat_history = dummy_chat_history['history']

    return {"session_id": session_id, "history": chat_history}

@router.websocket("/ws/{session_id}")
async def websocket_chat(session_id: UUID, websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 단순 에코 응답
            await websocket.send_text(f"LLM이 응답합니다: '{data}'")
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session_id: {session_id}")