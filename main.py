from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.setup import lifespan
from api.router import api_router


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix='/api')

# CORS 설정
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def root():
    return {'message': "Woori FISA 5th - Team 4 Backend Server"}