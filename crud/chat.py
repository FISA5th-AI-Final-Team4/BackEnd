from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from models import Chat, ChatbotResponse


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

async def creat_chatbot_chat(
    db: AsyncSession,
    session_id: UUID,
    persona_id: int,
    content: str,
    prompt_chat_id: int
) -> Chat:
    """
    챗봇 응답을 Chat 테이블과 ChatbotResponse 테이블에 트랜잭션으로 저장합니다.
    """
    new_chat = Chat(
        session_id=str(session_id),
        persona_id=persona_id,
        is_user=False,
        content=content
    )
    db.add(new_chat)
    await db.flush([new_chat])  # new_chat.id 값을 얻기 위해 flush 사용

    new_res_detail = ChatbotResponse(
        chat_id=new_chat.id,
        prompt_chat_id=prompt_chat_id
    )
    db.add(new_res_detail)
    await db.commit()
    
    return new_chat