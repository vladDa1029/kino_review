from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from app.application.queries.health import GetHealthHandler, HealthQuery
from app.presentation.schemas import HealthResponse

router = APIRouter(route_class=DishkaRoute)


@router.get("/health", response_model=HealthResponse, tags=["service"], summary="Health check")
async def healthcheck(handler: FromDishka[GetHealthHandler]) -> HealthResponse:
    status = await handler(HealthQuery())
    return HealthResponse(status=status.status, service=status.service)
