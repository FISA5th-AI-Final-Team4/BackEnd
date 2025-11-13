from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    # 시작 시점: DB 테이블 생성
    create_db_and_tables()
    print("✅ 백엔드 서버가 시작되었습니다.")
    yield
    # 종료 시점: 정리 작업 (필요 시 추가)
    print("🛑 백엔드 서버가 종료되었습니다.")