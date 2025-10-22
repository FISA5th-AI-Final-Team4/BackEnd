from fastapi import FastAPI

from api.router import api_router

app = FastAPI()

@app.get('/')
def root():
    return {'message': "Woori FISA 5th - Team 4 Backend Server"}

app.include_router(api_router, prefix='/api')