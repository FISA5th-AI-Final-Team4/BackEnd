from pydantic import BaseModel


class LoginRequest(BaseModel):
    session_id: str
    persona_id: int