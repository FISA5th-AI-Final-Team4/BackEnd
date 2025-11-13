from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from models import Persona


async def get_personas(db: AsyncSession) -> List[Persona]:
    """
    DB에서 모든 사용자 페르소나를 조회합니다.
    """
    statement = select(Persona)
    result = await db.execute(statement)
    
    return result.scalars().all()