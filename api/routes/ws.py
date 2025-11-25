from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timezone
from uuid import UUID

import json
import httpx
import asyncio

import crud.persona
import crud.qna

from api.routes.qna import faq_cache, terms_cache
from api.routes.chat import pending_session

from core.config import settings
from core.db import get_async_context_db


router = APIRouter(prefix="/chat", tags=["Chat"])

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    try:
        session_id_str = websocket.cookies.get("session_token")
        session_id = UUID(session_id_str)
    except Exception as e:
        await websocket.close(code=4001, reason="Invalid session")
        return
    # 세션 ID에 매핑된 페르소나 ID 조회
    persona_id = pending_session[session_id]
    async with get_async_context_db() as db:
        persona = await crud.persona.get_persona_by_id(db, persona_id)
        if not persona: # 존재하지 않는 페르소나 ID면 연결 종료
            await websocket.close(code=4001, reason="Invalid persona")
            return

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
                    timestamp = datetime.now(timezone.utc).isoformat()
                    res_payload = {
                        'sender': 'bot',
                        'timestamp': timestamp,
                        'message_id': str(user_chat.id)
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
                            res_payload['message'] = terms_cache[req_payload['message']]['answer']
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

                            if "tool_response" in payload and payload["tool_response"]:
                                print("Tool response detected in LLM reply.")
                                res_payload['message'] = payload["tool_response"]["answer"]
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