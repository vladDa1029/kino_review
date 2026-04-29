import asyncio

import pytest

from app.application.errors import AccessDeniedError
from app.presentation.access import ensure_admin_payload
from app.presentation.handlers import access_denied_error_handler


def test_ensure_admin_payload_allows_superuser() -> None:
    assert ensure_admin_payload({"is_superuser": True}) is None


def test_ensure_admin_payload_raises_access_denied() -> None:
    with pytest.raises(AccessDeniedError, match="Admin access required."):
        ensure_admin_payload({"is_superuser": False})


def test_access_denied_error_handler_returns_403() -> None:
    response = asyncio.run(
        access_denied_error_handler(
            request=None,
            exc=AccessDeniedError("Admin access required."),
        )
    )

    assert response.status_code == 403
    assert response.body == b'{"detail":"Admin access required."}'
