from collections.abc import Callable
from fnmatch import fnmatch

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import AuthGatewaySettings
from app.infrastructure.security.jwt_validator import JWTValidationError, JWTValidator
from app.presentation.middleware.user_headers import build_user_headers


class AuthGatewayMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        settings: AuthGatewaySettings,
        validator: JWTValidator,
        protected_paths: list[str] | None = None,
        public_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._settings = settings
        self._validator = validator
        self._protected_paths = protected_paths or []
        self._public_paths = public_paths or []

    async def dispatch(self, request: Request, call_next: Callable):
        if (
            request.method == "OPTIONS"
            or self._is_public_path(request.url.path)
            or not self._is_protected_path(request.url.path)
        ):
            return await call_next(request)

        token = _extract_bearer_token(request)
        if not token:
            return JSONResponse(
                status_code=401, content={"detail": "Not authenticated"}
            )

        try:
            payload = self._validator.decode(token)
        except JWTValidationError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        token_type = payload.get(self._settings.token_type_claim)
        if token_type and token_type != "access":
            return JSONResponse(
                status_code=401, content={"detail": "Invalid token type"}
            )

        user_id = payload.get(self._settings.user_id_claim)
        if not user_id:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        request.state.user_headers = build_user_headers(
            user_id=user_id,
            token_type=token_type,
            is_superuser=payload.get("is_superuser"),
        )
        request.state.user_payload = payload

        return await call_next(request)

    def _is_protected_path(self, path: str) -> bool:
        if not self._protected_paths:
            return False
        return any(fnmatch(path, pattern) for pattern in self._protected_paths)

    def _is_public_path(self, path: str) -> bool:
        if not self._public_paths:
            return False
        return any(fnmatch(path, pattern) for pattern in self._public_paths)


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
