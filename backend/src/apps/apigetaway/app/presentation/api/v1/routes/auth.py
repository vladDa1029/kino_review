from fnmatch import fnmatch

from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Request, Response
from dishka.integrations.fastapi import DishkaRoute
from fastapi.responses import JSONResponse
import httpx

from app.config import ProtectedPathsSettings, Services

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=DishkaRoute,
)


@router.get("/openapi.json", include_in_schema=False, response_model=None)
async def patched_openapi(
    client: FromDishka[httpx.AsyncClient],
    ser: FromDishka[Services],
    protected_settings: FromDishka[ProtectedPathsSettings],
) -> JSONResponse:
    spec = await fetch_and_patch_openapi(
        client=client,
        base_url=ser.auth,
        protected_patterns=protected_settings.patterns.get("auth", []),
    )
    return JSONResponse(spec)


@router.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], response_model=None
)
async def proxy_auth(
    request: Request,
    path: str,
    ser: FromDishka[Services],
    client: FromDishka[httpx.AsyncClient],
    schema: str = "http",
):
    url = f"{schema}://{ser.auth}/{path}"
    return await proxy_request(request, url, client=client)


async def proxy_request(
    request: Request,
    url: str,
    client: httpx.AsyncClient,
):
    req_body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

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


async def fetch_and_patch_openapi(
    client: httpx.AsyncClient,
    base_url: str,
    protected_patterns: list[str],
    schema: str = "http",
) -> dict:
    """
    Pull OpenAPI from the auth service, adjust basic metadata and mark protected endpoints.
    """
    try:
        resp = await client.get(f"{schema}://{base_url}/openapi.json")
        resp.raise_for_status()
        spec = resp.json()

        spec["info"]["title"] = "[PROXY] " + spec["info"].get("title", "Auth Service")

        if "servers" in spec:
            spec["servers"] = [{"url": "/"}]

        _mark_protected_endpoints_with_security(spec, protected_patterns)

        return spec

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Auth service unreachable: {e}")


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
