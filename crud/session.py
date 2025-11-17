from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from models import ChatSession


async def create_chat_session(
    db: AsyncSession,
    session_id: UUID,
    persona_id: int
) -> ChatSession:
    """
    새로운 채팅 세션을 생성합니다.
    """
    new_session = ChatSession(
        session_id=str(session_id),
        persona_id=persona_id
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return new_session

async def get_chat_session_by_id(
    db: AsyncSession,
    session_id: UUID
) -> ChatSession | None:
    """
    세션 ID로 채팅 세션을 조회합니다.
    """
    statement = (
        select(ChatSession).
        where(ChatSession.session_id == str(session_id))
    )
    result = await db.execute(statement)
    
    return result.scalar_one_or_none()