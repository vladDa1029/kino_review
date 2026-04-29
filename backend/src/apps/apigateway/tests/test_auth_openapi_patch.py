from app.presentation.api.v1.openapi_utils import (
    mark_protected_endpoints_with_security,
    strip_header_parameter,
)


def test_strip_header_parameter_removes_internal_auth_headers() -> None:
    spec = {
        "paths": {
            "/auth/users": {
                "get": {
                    "parameters": [
                        {"name": "X-User-Token-Type", "in": "header"},
                        {"name": "X-User-Is-Superuser", "in": "header"},
                        {"name": "page", "in": "query"},
                    ]
                }
            }
        }
    }

    strip_header_parameter(spec, "x-user-token-type")
    strip_header_parameter(spec, "x-user-is-superuser")

    assert spec["paths"]["/auth/users"]["get"]["parameters"] == [
        {"name": "page", "in": "query"}
    ]


def test_project_invitation_openapi_operation_is_marked_with_bearer_auth() -> None:
    spec = {
        "paths": {
            "/user/project-invitations/{token}": {
                "get": {
                    "parameters": [
                        {"name": "token", "in": "path"},
                        {"name": "x-user-id", "in": "header"},
                    ]
                }
            }
        }
    }

    mark_protected_endpoints_with_security(
        spec,
        patterns=["/user/project-invitations/*"],
    )
    strip_header_parameter(spec, "x-user-id")

    operation = spec["paths"]["/user/project-invitations/{token}"]["get"]
    assert operation["security"] == [{"bearerAuth": []}]
    assert operation["parameters"] == [{"name": "token", "in": "path"}]
