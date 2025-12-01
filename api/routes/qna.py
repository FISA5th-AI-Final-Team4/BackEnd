from fastapi import APIRouter, HTTPException

import crud.qna


router = APIRouter(prefix="/qna", tags=["QnA"])
faq_cache = {}
terms_cache = {}

@router.get("/faq")
async def get_high_views_faq(top_k: int=3):
    qna = await crud.qna.get_faqs_with_high_views(top_k=top_k)
    for qna_item in qna:
        faq_cache[qna_item['question']] = qna_item

    return qna

@router.get("/terms")
async def get_high_views_terms(top_k: int=6):
    qna = await crud.qna.get_terms_with_high_views(top_k=top_k)
    for qna_item in qna:
        terms_cache[qna_item['term']] = qna_item

    return qna

