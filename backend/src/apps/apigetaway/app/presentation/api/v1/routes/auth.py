from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Request, Response
from dishka.integrations.fastapi import DishkaRoute

from fastapi.responses import JSONResponse
import httpx

from app.config import Services

# TODO: Требуется рефакторинг так как код надо пересмотреть
# Часть надо перенести в infra
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=DishkaRoute,
)



@router.get("/openapi.json", include_in_schema=False, response_model=None)
async def patched_openapi(
    client: FromDishka[httpx.AsyncClient], ser: FromDishka[Services]
) -> JSONResponse:
    spec = await fetch_and_patch_openapi(client, ser.auth)
    return JSONResponse(spec)


@router.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], response_model=None
)
async def proxy_auth(
    request: Request,
    path: str,
    ser: FromDishka[Services],
    client: FromDishka[httpx.AsyncClient],
):
    url = f"http://{ser.auth}/{path}"
    return await proxy_request(request, url, client=client)


# Требуется разбить и сделать кастомные ошибки с перехватом
async def proxy_request(
    request: Request,
    url: str,
    client: httpx.AsyncClient,
):
    req_body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        # Делаем запрос через общий клиент
        resp = await client.request(
            method=request.method,
            url=url,
            content=req_body,
            headers=headers,
            params=request.query_params,
            follow_redirects=False,  # Лучше управлять вручную
        )

        # Создаём FastAPI Response с:
        # - телом
        # - статусом
        # - заголовками (включая Set-Cookie!)
        response = Response(
            content=resp.content,  # байты тела
            status_code=resp.status_code,
            headers=dict(resp.headers),  # включая Set-Cookie, CORS и др.
            media_type=resp.headers.get("content-type", "application/json"),
        )

        return response

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Service unreachable: {e}")


async def fetch_and_patch_openapi(client: httpx.AsyncClient, base_url: str) -> dict:
    """
    Внутренняя функция: получает и модифицирует OpenAPI-спеку.
    Не зависит от FastAPI, безопасна для вызова.
    """
    try:
        resp = await client.get(f"http://{base_url}/openapi.json")
        resp.raise_for_status()
        spec = resp.json()

        # Переписываем пути: /login → /auth/login
        spec["paths"] = {f"/auth{path}": value for path, value in spec["paths"].items()}

        # Обновляем заголовок
        spec["info"]["title"] = "[PROXY] " + spec["info"].get("title", "Auth Service")

        # Убираем servers
        if "servers" in spec:
            spec["servers"] = [{"url": "/"}]

        return spec

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Auth service unreachable: {e}")
