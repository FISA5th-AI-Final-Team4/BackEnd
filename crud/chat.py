from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from models import Chat


async def create_user_chat(
    db: AsyncSession,
    session_id: UUID,
    persona_id: int,
    content: str
) -> Chat:
    """
    사용자 채팅 메시지를 생성합니다.
    """
    new_chat = Chat(
        session_id=str(session_id),
        persona_id=persona_id,
        is_user=True,
        content=content
    )
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    
    return new_chat