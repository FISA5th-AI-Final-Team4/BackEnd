from fastapi import (
    APIRouter, HTTPException,
    Path, Body, Depends
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from uuid import UUID, uuid4
from typing import Dict

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
from core.db import SessionDep, get_async_context_db


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
async def get_chat_history(session_id: UUID, db: SessionDep):
    try:
        # 존재하지 않는 세션 ID면 404 에러 반환
        session = await crud.session.get_chat_session_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        chat_history = await crud.chat.fetch_chats_by_session_id(db, session_id)

        return {"session_id": session_id, "history": chat_history}
    except SQLAlchemyError as e:
        # DB 연결 실패, 쿼리 오류 등 SQLAlchemy 관련 오류가 발생한 경우
        print(f"--- DB Error in /history/{session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: DB operation failed"
        )
    except Exception as e:
        # 기타 알 수 없는 오류가 발생한 경우
        print(f"--- Unknown Error in /history/{session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error: Unknown error occurred"
        )

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