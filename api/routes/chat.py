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
        # TODO - session_id - persona_id 매핑 관리 Tuple로 변경 필요

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
        # TODO - session_id 없는 경우 예외처리 필요

dummy_personas, dummy_chat_history = _load_dummy_personas()
# TODO - pending_session set 생성 필요, session_id:persona_id 매핑 관리
manager = ConnectionManager()

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/personas", response_model=PersonaListResponse)
async def get_personas():
    # TODO - 페르소나 DB 연동 및 select 쿼리 필요 (controller/CRUD로 분리)
    return dummy_personas

@router.post("/session", response_model=ChatSessionResponse)
async def create_session(req: ChatSessionRequest):
    # 요청 body에 persona_id가 없으면 422 에러 반환
    if not req.persona_id:
        raise HTTPException(status_code=422, detail="persona_id is required")
    
    # 존재하지 않는 persona_id면 404 에러 반환
    if req.persona_id not in [p['id'] for p in dummy_personas['personas']]:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # 웹소켓 연결 및 세션 ID 반환
    session_id = uuid4()
    # TODO - pending_session에 session_id:persona_id 추가 필요
    
    return {"session_id": session_id}

@router.get("/history/{session_id}")
async def get_chat_history(session_id: UUID):
    # 존재하지 않는 세션 ID면 404 에러 반환
    if not session_id in manager.active_connections.keys():
        raise HTTPException(status_code=404, detail="Session not found")
    
    # TODO - 실제 DB에서 세션 ID로 채팅 히스토리 조회 필요
    chat_history = dummy_chat_history['history']

    return {"session_id": session_id, "history": chat_history}

@router.websocket("/ws/{session_id}")
async def websocket_chat(session_id: UUID, websocket: WebSocket):
    # TODO - pending_session에서 session_id 확인 필요 -> 없다면 4001 연결 거부
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 단순 에코 응답
            await websocket.send_text(f"LLM이 응답합니다: '{data}'")
    except WebSocketDisconnect:
        # TODO - 연결 종료 시 pending_session에서 session_id 제거 필요
        print(f"WebSocket disconnected for session_id: {session_id}")