import pytest
from fastapi.testclient import TestClient
from typing import List, Dict
from uuid import UUID

# API URL 접두사 (기존 코드와 동일)
API_PREFIX = "/api/chat"

# --- 5. (신규) 클라이언트 전체 시나리오 통합 테스트 ---
def test_full_chat_scenario(client: TestClient):
    """
    클라이언트의 실제 사용 흐름(시나리오)을 통합 테스트합니다.
    1. GET /personas : 사용 가능한 페르소나 목록을 조회합니다.
    2. POST /session : 페르소나를 선택하고 'session_id'를 발급받습니다.
    3. GET /history/{session_id} : 발급받은 ID로 초기 대화 기록을 조회합니다.
    4. WS /ws/{session_id} : 발급받은 ID로 웹소켓에 연결하고 메시지를 주고받습니다.
    """
    
    # --- 1. 페르소나 목록 조회 (GET /api/chat/personas) ---
    response = client.get(f"{API_PREFIX}/personas")

    assert response.status_code == 200
    personas_data = response.json()
    assert "personas" in personas_data
    assert isinstance(personas_data["personas"], List)
    assert len(personas_data["personas"]) > 0
    assert "id" in personas_data["personas"][0]

    print(f"시나리오 테스트: 페르소나 목록 획득 성공 ({len(personas_data['personas'])}개)")

    # --- 2. 세션 생성 (POST /api/chat/session) ---
    
    # 사용할 페르소나 ID (전달받은 페르소나 목록의 첫 번째 항목 사용)
    selected_persona_id = personas_data["personas"][0]["id"]

    response = client.post(f"{API_PREFIX}/session", json={"persona_id": selected_persona_id})
    
    assert response.status_code == 200
    session_data = response.json()
    assert "session_id" in session_data
    assert isinstance(session_data["session_id"], UUID)
    
    # 획득한 session_id를 변수에 저장합니다.
    session_id = session_data["session_id"]
    
    print(f"시나리오 테스트: 세션 ID 획득 성공 ({session_id})")

    # --- 3. 웹소켓 연결 및 채팅 (WS /api/chat/ws/{session_id}) ---
    llm_prefix = "LLM이 응답합니다: "
    # 2번 단계에서 획득한 'session_id'를 사용하여 웹소켓에 연결합니다.
    with client.websocket_connect(f"{API_PREFIX}/ws/{session_id}") as websocket:
        print(f"시나리오 테스트: WebSocket 연결 성공 (세션 ID: {session_id})")
        
        # 3-1. 첫 번째 메시지 전송 및 에코 응답 검증
        message_1 = "안녕하세요, 테스트 메시지입니다."
        websocket.send_text(message_1)
        
        response_1 = websocket.receive_text()
        expected_response_1 = f"{llm_prefix}'{message_1}'"
        assert response_1 == expected_response_1
        print("시나리오 테스트: 메시지 #1 전송 및 응답 검증 완료")
        
        # 3-2. 두 번째 메시지 전송 및 에코 응답 검증
        message_2 = "정상적으로 작동하는지 확인 중입니다."
        websocket.send_text(message_2)
        
        response_2 = websocket.receive_text()
        expected_response_2 = f"{llm_prefix}'{message_2}'"
        assert response_2 == expected_response_2
        print("시나리오 테스트: 메시지 #2 전송 및 응답 검증 완료")

    print(f"시나리오 테스트: WebSocket 연결 종료 및 전체 시나리오 성공")