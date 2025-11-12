from pydantic import BaseModel

from typing import List, Optional

from uuid import UUID

class Persona(BaseModel):
    id: int
    name: str
    description: str

class PersonaListResponse(BaseModel):
    personas: List[Persona]

class ChatSessionRequest(BaseModel):
    persona_id: int

class ChatSessionResponse(BaseModel):
    session_id: UUID

class ChatMessage(BaseModel):
    is_user: bool
    content: str

class ChatHistoryResponse(BaseModel):
    session_id: UUID
    history: List[ChatMessage]

class FeedbackRequest(BaseModel):
    message_id: UUID
    is_helpful: Optional[bool] = None
    prompt_message_id: UUID