import httpx
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.config import ProtectedPathsSettings, Services
from app.presentation.api.v1.openapi_utils import (
    mark_protected_endpoints_with_security,
    strip_header_parameter,
)

router = APIRouter(
    prefix="/project",
    tags=["project"],
    route_class=DishkaRoute,
)


@router.get("/openapi.json", include_in_schema=False, response_model=None)
async def patched_openapi(
    client: FromDishka[httpx.AsyncClient],
    ser: FromDishka[Services],
    protected_settings: FromDishka[ProtectedPathsSettings],
) -> JSONResponse:
    service_prefix = "project"
    spec = await fetch_and_patch_openapi(
        client=client,
        base_url=ser.project,
        service_prefix=service_prefix,
        protected_patterns=protected_settings.patterns.get(service_prefix, []),
    )
    return JSONResponse(spec)


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    response_model=None,
)
async def proxy_projects(
    request: Request,
    path: str,
    ser: FromDishka[Services],
    client: FromDishka[httpx.AsyncClient],
    schema: str = "http",
):
    url = f"{schema}://{ser.project}"
    if path:
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

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type", "application/json"),
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Service unreachable: {e}")


def _apply_user_headers(headers: dict[str, str], request: Request) -> None:
    headers.pop("x-user-id", None)
    headers.pop("x-user-token-type", None)
    user_headers = getattr(request.state, "user_headers", None)
    if user_headers:
        headers.update(user_headers)


async def fetch_and_patch_openapi(
    client: httpx.AsyncClient,
    base_url: str,
    service_prefix: str,
    protected_patterns: list[str],
    schema: str = "http",
) -> dict:
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

        mark_protected_endpoints_with_security(spec, protected_patterns)
        strip_header_parameter(spec, "x-user-id")

        return spec

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Project service unreachable: {e}")
