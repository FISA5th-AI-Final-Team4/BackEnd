from pydantic import BaseModel

from typing import List


class Persona(BaseModel):
    id: int
    name: str
    description: str

class PersonaListResponse(BaseModel):
    personas: List[Persona]