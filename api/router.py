from fastapi import APIRouter

from api.routes import health, chat, qna

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(qna.router)