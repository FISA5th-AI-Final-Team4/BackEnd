from sqlmodel import SQLModel

from typing import List, Optional

from uuid import UUID


class ChatSessionRequest(SQLModel):
    persona_id: int

class ChatSessionResponse(SQLModel):
    session_id: UUID

class ChatMessage(SQLModel):
    is_user: bool
    content: str

class ChatHistoryResponse(SQLModel):
    session_id: UUID
    history: List[ChatMessage]

class FeedbackRequest(SQLModel):
    message_id: UUID
    is_helpful: Optional[bool] = None