from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession
from sqlalchemy import text
from typing import List, Dict

from core.config import settings

qna_async_engine = create_async_engine(settings.FAQ_DATABASE_URL)

async def get_faqs_with_high_views(top_k: int=3) -> List[Dict]:
    """
    조회수가 높은 FAQ 항목들을 상위 K개 조회합니다.
    """

    query = """
    SELECT faq_id, question, answer, views
    FROM faqs
    ORDER BY views DESC
    LIMIT :top_k;
    """

    async with SQLModelAsyncSession(qna_async_engine) as db:
        result = await db.execute(
            text(query),
            {"top_k": top_k}
        )
    
    return result.mappings().all()

async def get_terms_with_high_views(top_k: int=6) -> List[Dict]:
    """
    조회수가 높은 용어 질문 항목들을 상위 K개 조회합니다.
    """

    # query = """
    # SELECT term_id, term, definition, views
    # FROM terms
    # ORDER BY views DESC
    # LIMIT :top_k;
    # """
    query = """
    SELECT term_id, term, definition
    FROM terms
    LIMIT :top_k;
    """

    async with SQLModelAsyncSession(qna_async_engine) as db:
        result = await db.execute(
            text(query),
            {"top_k": top_k}
        )
    
    return result.mappings().all()

async def increment_faq_view_count(question: str) -> None:
    """
    FAQ 항목의 조회수를 1 증가시킵니다.
    """

    query = """
    UPDATE faqs
    SET views = views + 1
    WHERE question = :question;
    """

    async with SQLModelAsyncSession(qna_async_engine) as db:
        await db.execute(
            text(query),
            {"question": question}
        )
        await db.commit()

async def increment_term_view_count(term: str) -> None:
    """
    용어 질문 항목의 조회수를 1 증가시킵니다.
    """

    query = """
    UPDATE terms
    SET views = views + 1
    WHERE term = :term;
    """

    async with SQLModelAsyncSession(qna_async_engine) as db:
        await db.execute(
            text(query),
            {"term": term}
        )
        await db.commit() 