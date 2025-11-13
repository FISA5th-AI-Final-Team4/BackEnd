from fastapi import FastAPI
from contextlib import asynccontextmanager

import json
from pathlib import Path
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.db import engine  # DB 엔진 (Session 생성용)
from models import Persona # 페르소나 DB 모델

# from core.db import create_db_and_tables


async def seed_initial_data():
    """
    JSON 파일에서 데이터를 로드하여 Persona 테이블을 시딩합니다.
    """
    print("🌱 초기 데이터(Seeding) 확인 중...")
    BASE_DIR = Path(__file__).resolve().parent.parent 
    DATA_FILE = BASE_DIR / "data" / "personas.json"

    try:
        async with AsyncSession(engine) as db:
            # 1. DB에 이미 데이터가 있는지 확인 (중복 방지)
            statement = select(Persona)
            existing_persona = (await db.exec(statement)).first()
            
            if existing_persona:
                print("... Persona 데이터가 이미 존재합니다. 시딩을 건너뜁니다.")
                return

            # 2. JSON 파일이 존재하는지 확인
            if not DATA_FILE.exists():
                print(f"WARN: {DATA_FILE} 파일이 없습니다. 시딩을 건너뜁니다.")
                return
                
            # 3. JSON 파일 로드
            print(f"... {DATA_FILE}에서 데이터를 로드합니다.")
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                personas_data = json.load(f)

            # 4. ORM 객체로 변환하여 세션에 추가
            personas_to_add = []
            for item in personas_data:
                # JSON 키가 Persona 모델의 필드와 일치해야 함
                # (일치하지 않으면 PersonaCreate 스키마로 한 번 감싸는 것이 좋음)
                new_persona = Persona(
                    name=item.get("name"),
                    description=item.get("description"),
                    # image_key=item.get("image_key"),
                )
                personas_to_add.append(new_persona)
            
            db.add_all(personas_to_add)
            await db.commit()
            print(f"✅ {len(personas_to_add)}개의 페르소나를 성공적으로 시딩했습니다.")

    except Exception as e:
        print(f"❌ 초기 데이터 시딩 중 오류 발생: {e}")
        # (필요 시 세션 롤백)
        # session.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    # 시작 시점: DB 테이블 생성
    print("🚀 백엔드 서버 시작 준비...")
    
    # ----- DB 테이블 생성 -----
    #   - 서버 시작 시 SQLModel의 메타데이터에 등록된 모든 테이블 DB에 생성
    #   - 이미 존재하는 경우 무시
    #   - run_sync를 이용하여 비동기 이벤트 루프 내에서 create_all 동기 함수 실행 
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    except Exception as e:
        print(f"❌ DB 테이블 생성 중 오류 발생: {e}")
        raise e

    # ----- 초기 데이터 시딩 -----
    #   - 서버 시작 시 각 테이블을 조회하고, 데이터가 없다면 초기 데이터 삽입
    await seed_initial_data()
    
    # --- 서버 실행 준비 완료 ---
    print("✅ 백엔드 서버가 시작되었습니다.")

    yield
    # --- 서버 종료 시점 ---
    print("🛑 백엔드 서버가 종료되었습니다.")
    # (필요 시 리소스 정리, 종료 작업 수행)