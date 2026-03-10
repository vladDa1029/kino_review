from app.application.errors.errors import AccessDeniedError, InvalidCredentialsError


def ensure_admin_headers(
    *,
    x_user_token_type: str | None,
    x_user_is_superuser: str | None,
) -> None:
    if x_user_token_type != "access":
        raise InvalidCredentialsError("Access token is required.")
    if x_user_is_superuser != "true":
        raise AccessDeniedError("Admin access required.")
