from app.application.errors import AccessDeniedError


def ensure_admin_payload(payload: dict | None) -> None:
    if not payload:
        return
    if payload.get("is_superuser") is not True:
        raise AccessDeniedError("Admin access required.")
