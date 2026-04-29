from fnmatch import fnmatch

from app.config import ProtectedPathsSettings
from app.presentation.middleware.user_headers import build_user_headers


def test_build_user_headers_includes_superuser_flag() -> None:
    headers = build_user_headers(
        user_id="user-id",
        token_type="access",
        is_superuser=True,
    )

    assert headers == {
        "x-user-id": "user-id",
        "x-user-token-type": "access",
        "x-user-is-superuser": "true",
    }


def test_project_report_paths_are_protected() -> None:
    settings = ProtectedPathsSettings()

    assert any(
        fnmatch("/project/reports/123", pattern)
        for pattern in settings.patterns["project"]
    )
