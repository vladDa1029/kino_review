from app.presentation.api.v1.openapi_utils import strip_header_parameter


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
