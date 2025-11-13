from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from typing import Annotated, AsyncGenerator

from core.config import settings
from models import Persona # 테이블 생성을 위해 임포트


# 비동기 DB 엔진 생성
engine = create_async_engine(settings.DATABASE_URL)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """ 비동기 DB 세션 생성 및 반환 """
    async with SQLModelAsyncSession(engine) as session: # ◀◀◀ 수정
        yield session

# 타입힌팅을 통한 DB 세션 의존성 주입
SessionDep = Annotated[AsyncSession, Depends(get_db)]