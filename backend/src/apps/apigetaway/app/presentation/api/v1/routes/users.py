from fnmatch import fnmatch

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import httpx

from app.config import ProtectedPathsSettings, Services

router = APIRouter(
    prefix="/user",
    tags=["user"],
    route_class=DishkaRoute,
)


@router.get("/openapi.json", include_in_schema=False, response_model=None)
async def patched_openapi(
    client: FromDishka[httpx.AsyncClient],
    ser: FromDishka[Services],
    protected_settings: FromDishka[ProtectedPathsSettings],
) -> JSONResponse:
    service_prefix = "user"
    spec = await fetch_and_patch_openapi(
        client=client,
        base_url=ser.user,
        service_prefix=service_prefix,
        protected_patterns=protected_settings.patterns.get(service_prefix, []),
    )
    return JSONResponse(spec)


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    response_model=None,
)
async def proxy_users(
    request: Request,
    path: str,
    ser: FromDishka[Services],
    client: FromDishka[httpx.AsyncClient],
    schema: str = "http",
):
    url = f"{schema}://{ser.user}"
    if path:
        path = _rewrite_user_path(path, request)
        url = f"{url}/{path}"
    return await proxy_request(request, url, client=client)


async def proxy_request(
    request: Request,
    url: str,
    client: httpx.AsyncClient,
):
    req_body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    _apply_user_headers(headers, request)

    try:
        resp = await client.request(
            method=request.method,
            url=url,
            content=req_body,
            headers=headers,
            params=request.query_params,
            follow_redirects=False,
        )

        response = Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type", "application/json"),
        )

        return response

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Service unreachable: {e}")


def _apply_user_headers(headers: dict[str, str], request: Request) -> None:
    headers.pop("x-user-id", None)
    headers.pop("x-user-token-type", None)
    user_headers = getattr(request.state, "user_headers", None)
    if user_headers:
        headers.update(user_headers)


def _rewrite_user_path(path: str, request: Request) -> str:
    user_headers = getattr(request.state, "user_headers", None)
    if not user_headers:
        return path
    user_id = user_headers.get("x-user-id")
    if not user_id:
        return path
    segments = path.lstrip("/").split("/")
    if len(segments) >= 2 and segments[0] == "users" and segments[1] == "me":
        segments[1] = str(user_id)
        return "/".join(segments)
    return path


async def fetch_and_patch_openapi(
    client: httpx.AsyncClient,
    base_url: str,
    service_prefix: str,
    protected_patterns: list[str],
    schema: str = "http",
) -> dict:
    """
    Pull OpenAPI from the user service, adjust metadata and mark protected endpoints.
    """
    try:
        resp = await client.get(f"{schema}://{base_url}/openapi.json")
        resp.raise_for_status()
        spec = resp.json()

        spec["paths"] = {
            f"/{service_prefix}{path}": value for path, value in spec["paths"].items()
        }

        fallback_title = f"{service_prefix.title()} Service"
        spec["info"]["title"] = "[PROXY] " + spec["info"].get("title", fallback_title)

        if "servers" in spec:
            spec["servers"] = [{"url": "/"}]

        _mark_protected_endpoints_with_security(spec, protected_patterns)
        _replace_user_id_paths(spec)
        _strip_header_parameter(spec, "x-user-id")

        return spec

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"User service unreachable: {e}")


def _mark_protected_endpoints_with_security(spec: dict, patterns: list[str]) -> None:
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


def _match_path(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _strip_header_parameter(spec: dict, header_name: str) -> None:
    _strip_parameter_from_spec(
        spec,
        name=header_name,
        location="header",
        case_insensitive=True,
    )


def _replace_user_id_paths(spec: dict) -> None:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return
    rewritten = {}
    for path, path_item in paths.items():
        if "/users/{user_id}" in path:
            new_path = path.replace("/users/{user_id}", "/users/me", 1)
            if isinstance(path_item, dict):
                _strip_parameter_from_path_item(
                    path_item,
                    name="user_id",
                    location="path",
                )
            rewritten[new_path] = path_item
        else:
            rewritten[path] = path_item
    spec["paths"] = rewritten


def _strip_parameter_from_spec(
    spec: dict,
    name: str,
    location: str | None = None,
    case_insensitive: bool = False,
) -> None:
    for path_item in spec.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        _strip_parameter_from_path_item(
            path_item,
            name=name,
            location=location,
            case_insensitive=case_insensitive,
        )


def _strip_parameter_from_path_item(
    path_item: dict,
    name: str,
    location: str | None = None,
    case_insensitive: bool = False,
) -> None:
    _strip_parameter_from_container(
        path_item,
        name=name,
        location=location,
        case_insensitive=case_insensitive,
    )
    for operation in path_item.values():
        if isinstance(operation, dict):
            _strip_parameter_from_container(
                operation,
                name=name,
                location=location,
                case_insensitive=case_insensitive,
            )


def _strip_parameter_from_container(
    container: dict,
    name: str,
    location: str | None,
    case_insensitive: bool,
) -> None:
    parameters = container.get("parameters")
    if not parameters:
        return
    name_key = name.lower() if case_insensitive else name
    filtered = []
    for param in parameters:
        if not isinstance(param, dict):
            filtered.append(param)
            continue
        param_name = param.get("name")
        param_in = param.get("in")
        if param_name is None:
            filtered.append(param)
            continue
        compare_name = str(param_name).lower() if case_insensitive else param_name
        matches_name = compare_name == name_key
        matches_location = location is None or param_in == location
        if matches_name and matches_location:
            continue
        filtered.append(param)
    if filtered:
        container["parameters"] = filtered
    else:
        container.pop("parameters", None)
