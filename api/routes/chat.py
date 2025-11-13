from fastapi import (
    APIRouter, HTTPException,
    WebSocket, WebSocketDisconnect,
    Path, Body, Depends
)

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Dict

import httpx

from schemas.chat import (
    ChatSessionRequest, ChatSessionResponse,
    ChatMessage, ChatHistoryResponse,
    FeedbackRequest
)
from schemas.persona import PersonaListResponse

from core.config import settings

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
    llm_endpoint = f"{settings.LLMSERVER_URL.rstrip('/')}/llm/mcp-router/dispatch"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            while True:
                data = await websocket.receive_text()
                
                print(f"Received message for session_id {session_id}: {data}")
                req_payload = {'sender': 'user', 'message': data}
                # TODO - 유저 채팅 저장 로직

                timestamp = datetime.now(timezone.utc).isoformat()
                message_id = uuid4()
                res_payload = {
                    'sender': 'bot',
                    'timestamp': timestamp,
                    'message_id': str(message_id)
                }

                print(f"Forwarding to LLM server at {llm_endpoint}")
                try:
                    response = await client.post(
                        llm_endpoint,
                        json={"query": data}
                    )
                    print("LLM server response received")
                    response.raise_for_status()
                    payload = response.json()
                    res_payload['message'] = payload.get("answer")
                    if not isinstance(res_payload['message'], str) or not res_payload['message']:
                        raise ValueError("LLM 서버 응답 형식이 올바르지 않습니다.")
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code

                    message = f"LLM 서버 오류 (HTTP {status})"
                    if isinstance(exc.response.text, str) and exc.response.text.strip():
                        res_payload['message'] = f"{message}: {exc.response.text.strip()}"
                except (httpx.RequestError, ValueError):
                    res_payload['message'] = "LLM 서버와의 통신 중 문제가 발생했습니다."
                finally:
                    # TODO - 봇 채팅 저장 로직
                    await websocket.send_json(res_payload)

        except WebSocketDisconnect:
            # TODO - 연결 종료 시 pending_session에서 session_id 제거 필요
            print(f"WebSocket disconnected for session_id: {session_id}")

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """
    챗봇 응답 메시지에 대한 피드백(thumb-up/down)을 제출받습니다.
    """
    
    # TODO 1: DB에서 req.message_id로 해당 메시지 조회
    # message = await get_message_from_db(req.message_id)
    
    # if not message:
    #     # 존재하지 않는 메시지 ID일 경우
    #     raise HTTPException(status_code=404, detail="Message not found")
        
    # if message.sender != 'bot':
    #     # 봇 메시지가 아닌 경우 (선택적 검증)
    #     raise HTTPException(status_code=400, detail="Feedback is only for bot messages")

    # TODO 2: DB의 해당 메시지 레코드에 피드백 상태 업데이트
    # await update_message_feedback(req.message_id, req.feedback.value) # req.feedback.value는 "up" 또는 "down"
    
    print(f"Feedback received for {req.message_id}: {req.is_helpful}")
    print(req)

    # 클라이언트에게 성공 응답 반환
    return {
        "status": "success", 
        "message_id": req.message_id, 
        "feedback_received": req.is_helpful
    }