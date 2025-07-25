from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.adapters.orm import start_mappers
from app.presentations.api import router as auth_router


app = FastAPI()
start_mappers()
# Настройка для разработки с React/Vue
origins = [
    "http://localhost:3000",  # React default
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",  # Alternative
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Cache-Control",
    ],
    expose_headers=["Content-Disposition"],
)
app.include_router(auth_router)
