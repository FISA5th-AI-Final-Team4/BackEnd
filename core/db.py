from typing import Annotated
from sqlmodel import SQLModel, create_engine, Session
from fastapi import Depends
from core.config import settings


engine = create_engine(settings.DATABASE_URL)
    
def create_db_and_tables():
    """ SQLModel로 정의한 테이블 생성 (이미 존재하는 경우 무시) """
    SQLModel.metadata.create_all(engine)

def get_db():
    """ DB 세션 생성 및 반환 """
    with Session(engine) as session:
        yield session

# 타입힌팅을 통한 DB 세션 의존성 주입
SessionDep = Annotated[Session, Depends(get_db)]