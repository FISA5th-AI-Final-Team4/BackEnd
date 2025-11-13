from sqlmodel import SQLModel

from typing import List, Optional

# ORM 상속용 기본 스키마
class PersonaBase(SQLModel):
    name: str
    description: Optional[str] = None
    # image_key: Optional[str] = None

# 페르소나 생성용 스키마
class PersonaCreate(PersonaBase):
    pass

# API 응답용 스키마
class PersonaRead(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    # image_key: Optional[str] = None

# API 응답용 페르소나 리스트 스키마
class PersonaListResponse(SQLModel):
    personas: List[PersonaRead]