from pydantic import BaseModel

from typing import List

class Persona(BaseModel):
    id: int
    name: str
    description: str

class PersonaListResponse(BaseModel):
    personas: List[Persona]

class ChatSessionRequest(BaseModel):
    persona_id: int

class ChatSessionResponse(BaseModel):
    session_id: str

class ChatMessage(BaseModel):
    is_user: bool
    content: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    history: List[ChatMessage]