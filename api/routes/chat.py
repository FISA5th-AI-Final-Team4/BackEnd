from fastapi import (
    APIRouter, HTTPException,
    WebSocket, WebSocketDisconnect,
    Path, Body, Depends
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Dict

import json
import httpx
import asyncio

from schemas.chat import (
    ChatSessionRequest, ChatSessionResponse,
    ChatMessage, ChatHistoryResponse,
    FeedbackRequest
)
from schemas.persona import PersonaListResponse

import crud.persona
import crud.session
import crud.chat

from core.config import settings
from core.db import SessionDep

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

# 서버에서 발급된 UUID인지 체크 및 세션&페르소나 매핑 담당
pending_session: Dict[UUID, int] = {}

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/personas", response_model=PersonaListResponse)
async def get_personas(db: SessionDep):
    """ 사용자 페르소나 목록을 조회합니다. """
    try:
        # DB에서 페르소나 목록 조회
        personas = await crud.persona.get_personas(db)
        return {"personas": personas}
    except SQLAlchemyError as e:
        # DB 연결 실패, 쿼리 오류 등 SQLAlchemy 관련 오류가 발생한 경우
        print(f"--- DB Error in /personas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: DB operation failed"
        )
    except Exception as e:
        # 기타 알 수 없는 오류가 발생한 경우
        print(f"--- Unknown Error in /personas: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Unknown error occurred"
        )

@router.post("/session")
async def create_session(req: ChatSessionRequest, db: SessionDep):
    try:
        # 요청 body에 persona_id가 없으면 422 에러 반환
        if not req.persona_id:
            raise HTTPException(status_code=422, detail="persona_id is required")
        
        # 존재하지 않는 persona_id면 404 에러 반환
        persona = await crud.persona.get_persona_by_id(db, req.persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # 웹소켓 연결을 위한 세션 ID를 쿠키로 반환
        session_id = uuid4()
        session_id_str = str(session_id)
        pending_session[session_id] = req.persona_id

        is_dev = (settings.ENVIRONMENT == "development")
        res = JSONResponse(content={"session_id": session_id_str})
        res.set_cookie(
            key="session_token",
            value=session_id_str,
            httponly=True,
            secure=not is_dev,
            samesite="lax",
            path="/"
        )
        
        return res

    except SQLAlchemyError as e:
        # DB 연결 실패, 쿼리 오류 등 SQLAlchemy 관련 오류가 발생한 경우
        print(f"--- DB Error in /session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: DB operation failed"
        )
    
    except Exception as e:
        # 기타 알 수 없는 오류가 발생한 경우
        print(f"--- Unknown Error in /session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Unknown error occurred"
        )

@router.get("/history/{session_id}")
async def get_chat_history(session_id: UUID):
    # 존재하지 않는 세션 ID면 404 에러 반환
    if not session_id in manager.active_connections.keys():
        raise HTTPException(status_code=404, detail="Session not found")
    
    # TODO - 실제 DB에서 세션 ID로 채팅 히스토리 조회 필요
    chat_history = dummy_chat_history['history']

    return {"session_id": session_id, "history": chat_history}

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket, db: SessionDep):
    try:
        session_id_str = websocket.cookies.get("session_token")
        session_id = UUID(session_id_str)
    except Exception as e:
        await websocket.close(code=4001, reason="Invalid session")
        return
    # 세션 ID에 매핑된 페르소나 ID 조회
    persona_id = pending_session[session_id]
    persona = await crud.persona.get_persona_by_id(db, persona_id)
    if not persona: # 존재하지 않는 페르소나 ID면 연결 종료
        await websocket.close(code=4001, reason="Invalid persona")
        return

    # PG 저장 예외 처리
    try:
        await crud.session.create_chat_session(db, session_id, persona_id)
    except SQLAlchemyError as e:
        print(f"--- DB Error in websocket /ws/{session_id}: {e}")
        await websocket.close(code=1011)
        return
    except Exception as e:
        print(f"--- Unknown Error in websocket /ws/{session_id}: {e}")
        await websocket.close(code=1011)
        return
    
    # WS 연결 수립
    await websocket.accept()
    llm_endpoint = f"{settings.LLMSERVER_URL.rstrip('/')}/llm/mcp-router/dispatch"
    print(f"WebSocket connection established for session_id: {session_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    # JSON 파싱 예외 처리
                    try:
                        req_payload = json.loads(data)
                        if not isinstance(req_payload, dict):
                            raise ValueError("Payload is not a JSON object")
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Invalid JSON received from {session_id}: {e}")
                        await websocket.send_json({"error": "Invalid JSON format"})
                        continue

                    # 사용자 메세지 DB 저장
                    try:
                        user_chat = await crud.chat.create_user_chat(
                            db, req_payload['message_id'],
                            session_id, persona_id, req_payload['message']
                        )
                    except SQLAlchemyError as e:
                        print(f"--- DB Error saving user chat for session_id {session_id}: {e}")
                        await websocket.send_json({"error": "Internal Server Error: DB operation failed"})
                        continue
                    timestamp = datetime.now(timezone.utc).isoformat()
                    res_payload = {
                        'sender': 'bot',
                        'timestamp': timestamp,
                        'message_id': str(user_chat.id)
                    }
                    print(f"Received message from session_id {session_id}: {req_payload['message']}")

                    # LLM 호출 및 응답 생성
                    try:
                        response = await client.post(
                            llm_endpoint,
                            json={"query": req_payload['message']}
                        )
                        response.raise_for_status()
                        payload = response.json()
                        res_payload['message'] = payload.get("answer")
                        if not isinstance(res_payload['message'], str) or not res_payload['message']:
                            raise ValueError("LLM 서버 응답 형식이 올바르지 않습니다.")
                    except httpx.HTTPStatusError as exc:
                        res_payload['message'] = f"LLM 서버 오류 (HTTP {exc.response.status_code})"
                    except (httpx.RequestError, ValueError) as e:
                        res_payload['message'] = f"LLM 서버 통신 오류: {e}"
                    # 봇 응답 전송&저장 병렬 처리
                    finally:
                        task_send_user = websocket.send_json(res_payload)
                        task_save_res = crud.chat.create_chatbot_chat(
                            db, session_id, persona_id,
                            res_payload['message'], user_chat.id 
                        )
                        try: 
                            await asyncio.gather(task_send_user, task_save_res)
                        except Exception as e:
                            print(f"Error during parallel send/save bot response: {e}")
                        print(f"Sent bot response to session_id {session_id}: {res_payload['message']}")
                # 루프 내부 개별 메세지 예외 처리
                except Exception as e:
                    print(f"--- Unknown Error in message handling loop for session_id {session_id}: {e}")
                    try:
                        await websocket.send_json({"error": "Internal Server Error: Unknown error occurred"})
                    except Exception:
                        pass
                    break
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session_id: {session_id}")
    except Exception as e:
        print(f"--- Unknown Error in websocket /ws/{session_id}: {e}")
        await websocket.close(code=1011)
    finally:
        # TODO - 연결 종료 시 항상 Manager에서 제거
        # manager.disconnect(session_id)
        print(f"WebSocket connection closed for session_id: {session_id}")

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, db: SessionDep):
    """
    챗봇 응답 메시지에 대한 피드백(thumb-up/down)을 제출받습니다.
    """
    
    try:
        chatbot_chat = await crud.chat.update_chat_feedback(
            db, req.message_id, req.is_helpful
        )
        print(f"Feedback received for {req.message_id}: {req.is_helpful}")
        print(req)
        print(chatbot_chat)

        # 클라이언트에게 성공 응답 반환
        return {
            "status": "success", 
            "message_id": chatbot_chat.chat_id, 
            "feedback_received": chatbot_chat.is_helpful
        }
    except SQLAlchemyError as e:
        print(f"--- DB Error in /feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: DB operation failed"
        )