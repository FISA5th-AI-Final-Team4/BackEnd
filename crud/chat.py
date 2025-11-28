from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID, uuid4

from models import Chat, ChatbotResponse


async def create_user_chat(
    db: AsyncSession,
    client_message_id: UUID,
    session_id: UUID,
    persona_id: int,
    content: str
) -> Chat:
    """
    사용자 채팅 메시지를 생성합니다.
    """
    new_chat = Chat(
        id=str(client_message_id),
        session_id=str(session_id),
        persona_id=persona_id,
        is_user=True,
        content=content
    )
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    
    return new_chat

async def create_chatbot_chat(
    db: AsyncSession,
    session_id: UUID,
    persona_id: int,
    content: str,
    prompt_chat_id: UUID,
    tool_name: Optional[str],
    tool_metadata: Optional[dict]
) -> Chat:
    """
    챗봇 응답을 Chat 테이블과 ChatbotResponse 테이블에 트랜잭션으로 저장합니다.
    """
    new_chat = Chat(
        id=str(uuid4()),
        session_id=str(session_id),
        persona_id=persona_id,
        is_user=False,
        content=content
    )
    db.add(new_chat)
    await db.flush([new_chat])  # new_chat.id 값을 얻기 위해 flush 사용

    new_res_detail = ChatbotResponse(
        chat_id=str(new_chat.id),
        prompt_chat_id=str(prompt_chat_id),
        source_tool=tool_name,
        response_payload=tool_metadata
    )
    db.add(new_res_detail)
    await db.commit()
    
    return new_chat

async def get_chat_by_id(db: AsyncSession, chat_id: UUID) -> Optional[Chat]:
    """
    주어진 ID에 해당하는 채팅을 조회합니다.
    """
    statement = (
        select(Chat)
        .where(Chat.id == str(chat_id))
    )
    result = await db.execute(statement)
    
    return result.scalars().first()

async def fetch_chats_by_session_id(db: AsyncSession, session_id: UUID) -> List[Chat]:
    """
    특정 세션 ID에 해당하는 모든 채팅 메시지를 조회합니다.
    """
    statement = (
        select(Chat)
        .where(Chat.session_id == str(session_id))
        .order_by(Chat.created_at)
    )
    result = await db.execute(statement)
    
    return result.scalars().all()

async def update_chat_feedback(
    db: AsyncSession, prompt_chat_id: UUID, is_helpful: bool
) -> Optional[ChatbotResponse]:
    """
    Args:
        db (AsyncSession): 데이터베이스 세션
        prompt_chat_id (UUID): 피드백 대상 챗봇 응답을 유발한 사용자의 메세지 ID
        is_helpful (bool): 유용함 여부 (True: 유용함, False: 유용하지 않음)
    Returns:
        Optional[ChatbotResponse]: 업데이트된 ChatbotResponse 객체 또는 None
    """

    statement = (
        select(ChatbotResponse)
        .where(
            ChatbotResponse.prompt_chat_id == str(prompt_chat_id)
        )
    )
    result = await db.execute(statement)
    res_to_update = result.scalars().first()

    if not res_to_update:
        return None  # ChatbotResponse가 없는 경우

    res_to_update.is_helpful = is_helpful
    db.add(res_to_update)
    await db.commit()
    await db.refresh(res_to_update)

    return res_to_update