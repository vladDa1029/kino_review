import pytest

from app.application.errors.errors import AccessDeniedError, InvalidCredentialsError
from app.presentations.access import ensure_admin_headers


def test_require_admin_access_allows_superuser() -> None:
    assert (
        ensure_admin_headers(
            x_user_token_type="access",
            x_user_is_superuser="true",
        )
        is None
    )


def test_require_admin_access_rejects_non_admin() -> None:
    with pytest.raises(AccessDeniedError):
        ensure_admin_headers(
            x_user_token_type="access",
            x_user_is_superuser="false",
        )


def test_require_admin_access_rejects_non_access_token() -> None:
    with pytest.raises(InvalidCredentialsError):
        ensure_admin_headers(
            x_user_token_type="refresh",
            x_user_is_superuser="true",
        )
