import pytest
import json
import os

from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module") # 'module' scope: 이 파일의 테스트 실행 시 딱 한 번만 실행
def client():
    """
    모든 테스트에서 공통으로 사용할 TestClient를 생성합니다.
    """
    with TestClient(app) as c:
        yield c # 'return' 대신 'yield'를 사용하면 테스트 종료 후 후처리(정리) 가능

@pytest.fixture(scope="session") # 'session' scope: pytest 실행 시 딱 한 번만 실행
def dummy_personas():
    """
    tests/data/personas.json 파일을 읽어서 파이썬 객체(리스트)로 반환합니다.
    """
    # 현재 conftest.py 파일의 위치를 기준으로 경로 설정
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "data", "personas.json")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@pytest.fixture(scope="session") # 'session' scope: pytest 실행 시 딱 한 번만 실행
def dummy_chat_history():
    """
    tests/data/chat_history.json 파일을 읽어서 파이썬 객체(딕셔너리)로 반환합니다.
    """
    # 현재 conftest.py 파일의 위치를 기준으로 경로 설정
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "data", "chat_history.json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data