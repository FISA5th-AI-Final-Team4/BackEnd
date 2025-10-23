import pytest
from fastapi.testclient import TestClient

from typing import List, Dict

# API URL 접두사
API_PREFIX = "/api/chat"

# --- 1. /api/chat/personas 테스트 ---
def test_get_personas_success(
    client: TestClient,
    dummy_personas: Dict[str, List[Dict[str, str]]]
):
    """
    GET /api/chat/personas 엔드포인트가
    1. 200 OK를 반환하는지
    2. 'tests/data/personas.json'의 내용과 일치하는 응답을 반환하는지 검증
    """
    response = client.get(f"{API_PREFIX}/personas")
    
    # 1. 200 OK 검증
    assert response.status_code == 200
    
    # 2. 응답 데이터가 픽스처(JSON)와 정확히 일치하는지 검증
    data = response.json()
    assert data == dummy_personas

# --- 2. /api/chat/session 테스트 ---
def test_create_session_success(
    client: TestClient,
    dummy_personas: Dict[str, List[Dict[str, str]]]
):
    """
    POST /api/chat/session 엔드포인트가
    1. 유효한 persona_id를 보냈을 때 200 OK를 반환하는지
    2. 응답에 session_id 필드가 문자열로 포함되는지 테스트
    """
    # 픽스처 데이터의 첫 번째 페르소나 ID를 사용 (데이터 일관성 유지)
    valid_persona_id = dummy_personas["personas"][0]["id"]
    request_body = {"persona_id": valid_persona_id}
    
    response = client.post(f"{API_PREFIX}/session", json=request_body)
    
    # 1. 200 OK 검증
    assert response.status_code == 200
    
    # 2. 응답 구조 검증
    data = response.json()
    assert "session_id" in data
    assert isinstance(data["session_id"], str)

def test_create_session_missing_body(client: TestClient):
    """
    Pydantic 모델 유효성 검사 테스트
    1. persona_id 없이(빈 body) 요청 시 422 에러를 반환하는지 테스트
    """
    response = client.post(f"{API_PREFIX}/session", json={})
    
    # 422 Unprocessable Entity 검증
    assert response.status_code == 422

# --- 3. /api/chat/history/{session_id} 테스트 ---
def test_get_chat_history_success(
    client: TestClient,
    dummy_chat_history: Dict[str, List[Dict[str, str | bool]]]
):
    """
    GET /api/chat/history/{session_id} 엔드포인트가
    1. 200 OK를 반환하는지
    2. 응답이 dict인지 테스트
    """
    test_session_id = dummy_chat_history["session_id"]
    
    response = client.get(f"{API_PREFIX}/history/{test_session_id}")
    
    # 1. 200 OK 검증
    assert response.status_code == 200
    
    # 2. dict인지 검증
    data = response.json()
    assert isinstance(data, dict)
    
    # 히스토리 구조 검증
    assert "session_id" in data
    assert "history" in data
    if "history" in data:
        for message in data["history"]:
            assert "is_user" in message
            assert "content" in message

# --- 4. /api/chat/ws/{session_id} 테스트 ---
def test_websocket_chat_echo(
    client: TestClient,
    dummy_chat_history: Dict[str, List[Dict[str, str | bool]]]
):
    """
    WS /api/chat/ws/{session_id} 웹소켓 엔드포인트가
    1. 연결을 수락(accept)하는지
    2. 메시지를 보냈을 때, (LLM 로직 대신) 에코 응답을 반환하는지 테스트
    """
    test_session_id = dummy_chat_history["session_id"]
    
    # 주입된 client의 웹소켓 클라이언트를 사용
    with client.websocket_connect(f"{API_PREFIX}/ws/{test_session_id}") as websocket:
        
        # 1. 테스트 메시지 전송
        test_message = "안녕하세요?"
        websocket.send_text(test_message)
        
        # 2. 서버로부터 응답 수신
        response_text = websocket.receive_text()
        
        # 3. 응답 검증 (router.py 예제 코드의 임시 응답 기준)
        expected_response = f"LLM이 응답합니다: '{test_message}'"
        assert response_text == expected_response
        
        # 4. (추가) 두 번째 메시지 테스트
        test_message_2 = "두 번째 메시지"
        websocket.send_text(test_message_2)
        response_text_2 = websocket.receive_text()
        expected_response_2 = f"LLM이 응답합니다: '{test_message_2}'"
        assert response_text_2 == expected_response_2

    # `with` 블록이 끝나면 웹소켓 연결은 자동으로 닫힙니다.