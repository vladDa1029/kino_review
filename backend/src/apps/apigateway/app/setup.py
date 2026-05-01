# Функции для настройки main фабрик.
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import AuthGatewaySettings, ProtectedPathsSettings
from app.infrastructure.security.jwt_validator import JWTValidator
from app.presentation.middleware.auth import AuthGatewayMiddleware


# Настройку CORS
def CORS_Middleware(app: FastAPI):
    context = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",  # Alternative
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=context,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
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


def AuthGateway_Middleware(
    app: FastAPI,
    settings: AuthGatewaySettings,
    protected_paths: ProtectedPathsSettings,
) -> FastAPI:
    validator = JWTValidator(
        public_key=settings.public_key,
        algorithm=settings.algorithm,
    )
    flattened_patterns = [
        pattern
        for patterns in protected_paths.patterns.values()
        for pattern in patterns
    ]
    if "/admin/user*" not in flattened_patterns:
        flattened_patterns.append("/admin/user*")
    public_patterns = [
        "/admin/user/openapi.json",
        "/admin/user/docs",
        "/admin/user/redoc",
        "/user/confirmations/*",
    ]
    app.add_middleware(
        AuthGatewayMiddleware,
        settings=settings,
        validator=validator,
        protected_paths=flattened_patterns,
        public_paths=public_patterns,
    )
    return app
