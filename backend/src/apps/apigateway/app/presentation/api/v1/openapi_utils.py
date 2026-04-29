from fnmatch import fnmatch


def mark_protected_endpoints_with_security(spec: dict, patterns: list[str]) -> None:
    if not patterns:
        return

    components = spec.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.setdefault(
        "bearerAuth",
        {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    )

    for path, operations in spec.get("paths", {}).items():
        if not _match_path(path, patterns):
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation.setdefault("security", [{"bearerAuth": []}])


def strip_header_parameter(spec: dict, header_name: str) -> None:
    for path_item in spec.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        _strip_parameter_from_container(path_item, header_name)
        for operation in path_item.values():
            if isinstance(operation, dict):
                _strip_parameter_from_container(operation, header_name)


def _strip_parameter_from_container(container: dict, header_name: str) -> None:
    parameters = container.get("parameters")
    if not parameters:
        return
    filtered = []
    for param in parameters:
        if not isinstance(param, dict):
            filtered.append(param)
            continue
        param_name = str(param.get("name", "")).lower()
        param_in = param.get("in")
        if param_name == header_name.lower() and param_in == "header":
            continue
        filtered.append(param)
    if filtered:
        container["parameters"] = filtered
    else:
        container.pop("parameters", None)


def _match_path(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)
