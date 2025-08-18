# Функции для настройки main фабрик.
from typing import Any, AsyncIterator, Generator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx


# Настройку CORS
def CORS_Middleware(app: FastAPI):
    context = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",  # Alternative
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=context,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Cache-Control",
        ],
    )
    return app


async def get_aclient() -> AsyncIterator[httpx.AsyncClient]:
    client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    yield client
    await client.aclose()
