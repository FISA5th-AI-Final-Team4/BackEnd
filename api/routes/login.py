from fastapi import (
    APIRouter, HTTPException,
    Path, Body, Depends
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import httpx
import asyncio

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Dict

from schemas.chat import (
    ChatSessionRequest, ChatSessionResponse,
    ChatMessage, ChatHistoryResponse,
    FeedbackRequest
)
from schemas.persona import PersonaRequest, PersonaListResponse
from schemas.login import LoginRequest

import crud.persona
import crud.session
import crud.chat

from core.config import settings
from core.db import SessionDep, get_async_context_db

from api.routes.ws import connection_manager

router = APIRouter(prefix="/login", tags=["Login"])

@router.post("/")
async def login(req: LoginRequest, db: SessionDep):
    """
        사용자 로그인 처리 엔드포인트
        바디에 포함된 세션 ID가 connection_manager에 존재하는지 확인
        존재하면 해당 세션과 바디에 포함된 페르소나 ID를 매핑하여 업데이트
    """
    req_session_id = UUID(req.session_id)
    if not req_session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    
    # 실제 서비스에서는 로그인 처리 로직 구현
    # connection_manager에 세션 ID가 존재하는지 확인
    if req_session_id not in connection_manager.active_connections:
        # 존재하지 않는 세션ID로 요청한 경우
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # 세션과 페르소나 매핑 업데이트
        print(f"Update persona_id to {req.persona_id} in session {req_session_id}")
        connection_manager.update_persona_id(req_session_id, req.persona_id)
        await crud.session.update_persona_in_session(
            db,
            req_session_id,
            connection_manager.active_connections[req_session_id]["persona_id"]
        )

        try:
            # 로그인 조건은 MCP 소비 데이터 추천 요청이므로 바로 MCP 소비데이터 추천 함수 호출
            print("Call MCP server directly for consumption recommendation after login.")
            async with httpx.AsyncClient(timeout=settings.HTTPX_TIMEOUT) as client:
                mcp_response = await client.post(
                    f"{settings.MCP_SERVER_URL}/tools/consumption_recommend",
                    json={
                        "session_id": str(req_session_id),
                        "persona_id": connection_manager.active_connections[req_session_id]["persona_id"]
                    }
                )
                mcp_response.raise_for_status()
                payload = mcp_response.json()
                print(f"MCP response payload: {payload}")

                timestamp = datetime.now(timezone.utc).isoformat()
                res_payload = {
                        'sender': 'bot',
                        'timestamp': timestamp,
                        'message_id': str(
                            connection_manager.active_connections[req_session_id]["user_chat_id"]
                        ),
                        'login_required': False,
                        'message': payload['answer'],
                        'card_list': payload['card_list']
                    }
                print(f"---[/api/login/] Response payload to send: {res_payload}")

                tool_metadata = {
                    'card_list': res_payload['card_list'],
                    'login_required': res_payload['login_required']
                }
                try:
                    # 챗봇 응답 전송 & 저장 병렬 처리
                    async with get_async_context_db() as db:
                        task_send_user = connection_manager.active_connections[req_session_id]["websocket"].send_json(res_payload)
                        task_save_res = crud.chat.create_chatbot_chat(
                            db, req_session_id, connection_manager.active_connections[req_session_id]["persona_id"],
                            res_payload['message'], connection_manager.active_connections[req_session_id]["user_chat_id"],
                            "consumption_recommend", tool_metadata
                        )
                        await asyncio.gather(task_send_user, task_save_res)
                except Exception as e:
                    print(f"Error during parallel send/save bot response: {e}")
                print(f"Sent bot response to session_id {req_session_id}: {res_payload['message']}")
                
        except httpx.RequestError as e:
            print(f"--- HTTPX Request Error to MCP Server: {e}")
            raise HTTPException(
                status_code=502,
                detail="Bad Gateway: MCP server request failed"
            )

    except SQLAlchemyError as e:
        print(f"--- DB Error in /login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: DB operation failed"
        )
    except Exception as e:
        print(f"--- Unknown Error in /login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Unknown error occurred"
        )

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

@router.post("/persona_id")
async def get_persona_id(req: PersonaRequest):
    """ ConnectionManager의 세션ID에 페르소나ID가 매핑되어 있는지 확인 """
    req_session_id = UUID(req.session_id)
    if not req_session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    
    # 실제 서비스에서는 로그인 처리 로직 구현
    # connection_manager에 세션 ID가 존재하는지 확인
    if req_session_id not in connection_manager.active_connections:
        # 존재하지 않는 세션ID로 요청한 경우
        raise HTTPException(status_code=404, detail="Session not found")

    # 페르소나 ID 반환
    return {
        "persona_id": connection_manager.active_connections[req_session_id]["persona_id"]
    }