from fastapi import FastAPI


app = FastAPI()

@app.get('/')
def root():
    return {'message': "Woori FISA 5th - Team 4 Backend Server"}