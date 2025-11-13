from sqlmodel import SQLModel

from typing import List


class Persona(SQLModel):
    id: int
    name: str
    description: str

class PersonaListResponse(SQLModel):
    personas: List[Persona]