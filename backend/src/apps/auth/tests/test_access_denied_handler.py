import asyncio

from app.application.errors.errors import AccessDeniedError
from app.presentations.handlers import access_denied_error_handler


def test_access_denied_handler_returns_403_message() -> None:
    response = asyncio.run(
        access_denied_error_handler(
            request=None,
            exc=AccessDeniedError("Admin access required."),
        )
    )

    assert response.status_code == 403
    assert response.body == b'{"message":"Insufficient permissions for this token."}'
