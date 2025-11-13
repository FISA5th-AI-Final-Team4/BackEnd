from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, TEXT, JSON, TIMESTAMP, String
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import CHAR

from typing import List, Optional
from datetime import datetime, timezone

from schemas.persona import PersonaBase


class Persona(PersonaBase, table=True):
    __tablename__ = "Persona" # DB에 저장되는 테이블 이름

    # DB 기본키 컬럼
    id: Optional[int] = Field(default=None, primary_key=True)

    # DB 제약조건 추가를 위해 Field 재정의
    name: str = Field(max_length=100, unique=True, nullable=False)
    description: Optional[str] = Field(default=None, max_length=255)
    # image_key: Optional[str] = Field(default=None, max_length=255) # S3 이미지 키

    # 페르소나 생성 시점 타임스탬프 컬럼
    created_at: datetime = Field(
        # Python에서 ORM 객체 생성 시 기본값
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column=Column(
            TIMESTAMP(timezone=True),  # DB에 저장되는 실제 컬럼 타입
            server_default=func.now(), # DB 서버에 실제로 저장될 때의 기본값
            nullable=False
        )
    )