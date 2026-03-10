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
