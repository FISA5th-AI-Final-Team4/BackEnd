from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timezone
from uuid import UUID, uuid4

import json
import httpx
import asyncio

import crud.session
import crud.persona
import crud.qna
import crud.chat

from api.routes.qna import faq_cache, terms_cache
from api.routes.chat import pending_session

from core.config import settings
from core.db import get_async_context_db


router = APIRouter(prefix="/chat", tags=["Chat"])

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    # WS 최초 연결 시 랜덤 UUID & 빈 페르소나 ID (로그아웃 상태) 쌍 생성
        # 추후 로그인 시 페르소나 ID 업데이트
    session_id = uuid4()
    persona_id = None
    pending_session[session_id] = persona_id

    # PG 저장 예외 처리
    try:
        async with get_async_context_db() as db:
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
        async with httpx.AsyncClient(timeout=settings.HTTPX_TIMEOUT) as client:
            while True:
                try:
                    # 사용자가 전송한 데이터 변수화
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
                        async with get_async_context_db() as db:
                            user_chat = await crud.chat.create_user_chat(
                                db, req_payload['message_id'],
                                session_id, persona_id, req_payload['message']
                            )
                    except SQLAlchemyError as e:
                        print(f"--- DB Error saving user chat for session_id {session_id}: {e}")
                        await websocket.send_json({"error": "Internal Server Error: DB operation failed"})
                        continue
                    # 사용자에게 WS로 전송할 페이로드 준비
                    timestamp = datetime.now(timezone.utc).isoformat()
                    res_payload = {
                        'sender': 'bot',
                        'timestamp': timestamp,
                        'message_id': str(user_chat.id),
                        'login_required': False
                    }
                    print(f"Received message from session_id {session_id}: {req_payload['message']}")
                    
                    try:
                        # 캐싱된 QnA 질문인지 확인
                        # faq 캐시 확인
                        if req_payload['message'] in faq_cache:
                            # 있는 경우 view 수 증가 및 바로 응답
                            res_payload['message'] = faq_cache[req_payload['message']]['answer']
                            await crud.qna.increment_faq_view_count(req_payload['message'])
                            print(f"FAQ cache hit: {req_payload['message']} -> {res_payload['message']}")
                        # term 캐시 확인
                        elif req_payload['message'] in terms_cache:
                            # 있는 경우 view 수 증가 및 바로 응답
                            res_payload['message'] = terms_cache[req_payload['message']]['definition']
                            await crud.qna.increment_term_view_count(req_payload['message'])
                            print(f"Term cache hit: {req_payload['message']} -> {res_payload['message']}")
                        # LLM 호출 및 응답 생성 (캐싱된 답변이 없는 경우)
                        else:
                            response = await client.post(
                                llm_endpoint,
                                json={"query": req_payload['message']}
                            )
                            response.raise_for_status()
                            payload = response.json()

                            # 툴이 호출된 응답인 경우
                            if "tool_response" in payload and payload["tool_response"]:
                                print("Tool response detected in LLM reply.")
                                res_payload['message'] = payload["tool_response"]["answer"]
                                # 로그인이 필요한 툴 호출인 경우
                                if "login_required" in payload["tool_response"]:
                                    res_payload['login_required'] = True
                            # 챗봇 표준 응답인 경우
                            else:
                                print("Standard LLM response detected.")
                                res_payload['message'] = payload["answer"]
                            if not isinstance(res_payload['message'], str) or not res_payload['message']:
                                raise ValueError("LLM 서버 응답 형식이 올바르지 않습니다.")
                    except httpx.HTTPStatusError as exc:
                        res_payload['message'] = f"LLM 서버 오류 (HTTP {exc.response.status_code})"
                    except (httpx.RequestError, ValueError) as e:
                        res_payload['message'] = f"LLM 서버 통신 오류: {e}"
                    # 봇 응답 전송&저장 병렬 처리
                    finally:
                        try:
                            # 챗봇 응답 전송 & 저장 병렬 처리
                            async with get_async_context_db() as db:
                                task_send_user = websocket.send_json(res_payload)
                                task_save_res = crud.chat.create_chatbot_chat(
                                    db, session_id, persona_id,
                                    res_payload['message'], user_chat.id 
                                )
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
        print(f"WebSocket connection closed for session_id: {session_id}")