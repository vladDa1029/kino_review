from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["documentation"])

templates = Jinja2Templates(directory="app/presentation/templates/docs/")


@router.get("/", include_in_schema=False)
async def docs_hub(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/{service}/docs", include_in_schema=False)
async def service_docs_page(request: Request, service: str):

    return templates.TemplateResponse(
        "open_docs.html", {"request": request, "service": service}
    )


@router.get("/{service}/redoc", include_in_schema=False)
async def service_redoc_page(request: Request, service: str):
    return templates.TemplateResponse(
        "redoc.html", {"request": request, "service": service}
    )


@router.get("/admin/user/docs", include_in_schema=False)
async def admin_user_docs_page(request: Request):
    return templates.TemplateResponse(
        "open_docs.html", {"request": request, "service": "admin/user"}
    )


@router.get("/admin/user/redoc", include_in_schema=False)
async def admin_user_redoc_page(request: Request):
    return templates.TemplateResponse(
        "redoc.html", {"request": request, "service": "admin/user"}
    )
