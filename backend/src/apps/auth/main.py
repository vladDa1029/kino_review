from fastapi import FastAPI
from app.adapters.orm import start_mappers
from app.presentations.api import router as auth_router


app = FastAPI()
start_mappers()

app.include_router(auth_router)
