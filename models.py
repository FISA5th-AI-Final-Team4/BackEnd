from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column, ForeignKey, Index,
    TEXT, JSON, TIMESTAMP, 
    String, Integer
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import CHAR

from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4

from schemas.persona import PersonaBase


def get_timestamp_column():
    """타임스탬프 컬럼 생성 헬퍼 함수"""
    return Column(
        TIMESTAMP(timezone=True),  # DB에 저장되는 실제 컬럼 타입
        server_default=func.now(), # DB 서버에 실제로 저장될 때의 기본값
        nullable=False
    )

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
        sa_column=get_timestamp_column()
    )

    # --- Relationships ---
    # (Ref: ChatSession.persona_id > Persona.id)
    chat_sessions: List["ChatSession"] = Relationship(back_populates="persona")
    chats: List["Chat"] = Relationship(back_populates="persona")

class ChatSession(SQLModel, table=True):
    __tablename__ = "ChatSession"

    # Primary Key
    session_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(CHAR(36), primary_key=True) # UUID를 CHAR(36)로 저장
    )
    
    # Foreign Key - Persona.id (페르소나 삭제 시 NULL로 변경)
    persona_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("Persona.id", ondelete="SET NULL"))
    )

    # 세션 생성 시점 타임스탬프 컬럼
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column=get_timestamp_column()
    )

    # --- Relationships ---
    persona: Optional[Persona] = Relationship(back_populates="chat_sessions")
    chats: List["Chat"] = Relationship(
        back_populates="session",
        # 'ChatSession'이 삭제될 때 관련된 모든 'Chat' 메시지를 연쇄 삭제
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Chat(SQLModel, table=True):
    __tablename__ = "Chat"
    
    # 인덱스 설정하여 성능 최적화
    __table_args__ = (
        Index("idx_session_created", "session_id", "created_at"),
    )

    # Primary Key
    id: UUID = Field(
        sa_column=Column(CHAR(36), primary_key=True)
    )
    
    # Foreign Key - ChatSession.session_id
    session_id: UUID = Field(
        sa_column=Column(
            CHAR(36),
            ForeignKey("ChatSession.session_id", ondelete="CASCADE"), 
            nullable=False
        )
    )

    # Foreign Key - Persona.id
    persona_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("Persona.id", ondelete="SET NULL"))
    )
    
    # 사용자 채팅 여부
    is_user: bool
    
    # 실제 채팅 내용
    content: str = Field(sa_column=Column(TEXT, nullable=False))
    
    # 채팅 생성 시점 타임스탬프 컬럼
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column=get_timestamp_column()
    )

    # --- Relationships ---
    session: ChatSession = Relationship(back_populates="chats")
    persona: Optional[Persona] = Relationship(back_populates="chats")
    response_detail: Optional["ChatbotResponse"] = Relationship(
        back_populates="chat",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "ChatbotResponse.chat_id"
        }
    )
    prompted_responses: List["ChatbotResponse"] = Relationship(
        back_populates="prompt_chat",
        sa_relationship_kwargs={"foreign_keys": "ChatbotResponse.prompt_chat_id"}
    )

class ChatbotResponse(SQLModel, table=True):
    __tablename__ = "ChatbotResponse"

    # Foreign Key - Chat.id (is_user가 False인 챗봇 응답 메시지 ID)
    chat_id: UUID = Field(
        sa_column=Column(
            CHAR(36), ForeignKey("Chat.id", ondelete="CASCADE"), 
            primary_key=True
        )
    )
    
    # Foreign Key - Chat.id (챗봇 응답을 유발한 사용자의 프롬프트 메시지 ID)
    prompt_chat_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(CHAR(36), ForeignKey("Chat.id", ondelete="SET NULL"))
    )

    # True: 유용함, False: 유용하지 않음, None: 미평가 (기본값)
    is_helpful: Optional[bool] = Field(default=None)

    # TODO - 호출된 도구 정보 컬럼 / 응답 타입 컬럼 (카드 정보, 일반 채팅 등)

    # --- Relationships ---
    chat: Chat = Relationship(
        back_populates="response_detail",
        sa_relationship_kwargs={"foreign_keys": "ChatbotResponse.chat_id"}
    )
    
    prompt_chat: Optional[Chat] = Relationship(
        back_populates="prompted_responses",
        sa_relationship_kwargs={"foreign_keys": "ChatbotResponse.prompt_chat_id"}
    )