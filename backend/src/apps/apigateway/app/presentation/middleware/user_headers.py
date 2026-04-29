def build_user_headers(
    *,
    user_id: str,
    token_type: str | None,
    is_superuser: bool | None = None,
) -> dict[str, str]:
    headers = {"x-user-id": str(user_id)}
    if token_type:
        headers["x-user-token-type"] = str(token_type)
    if is_superuser is not None:
        headers["x-user-is-superuser"] = str(is_superuser).lower()
    return headers
