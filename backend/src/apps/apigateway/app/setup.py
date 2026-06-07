# Функции для настройки main фабрик.
import http.cookiejar
from collections.abc import AsyncIterator

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


class _RejectAllCookiePolicy(http.cookiejar.DefaultCookiePolicy):
    """Refuse to ever store a cookie.

    The gateway proxies requests through a single shared ``httpx.AsyncClient``.
    httpx clients keep a cookie jar by default, so an upstream ``Set-Cookie``
    (e.g. the auth service ``refresh`` cookie) would be captured once and then
    silently replayed on every subsequent proxied request — leaking one user's
    session to everyone else. The proxy forwards the caller's ``Cookie`` header
    and the upstream ``Set-Cookie`` header verbatim, so the client itself must
    stay completely stateless about cookies.
    """

    def set_ok(self, cookie, request) -> bool:  # noqa: ANN001 - urllib signature
        return False


async def get_aclient() -> AsyncIterator[httpx.AsyncClient]:
    client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        cookies=http.cookiejar.CookieJar(policy=_RejectAllCookiePolicy()),
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
