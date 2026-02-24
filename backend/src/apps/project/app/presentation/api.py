from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from app.application.commands.publish_demo_event import (
    PublishDemoEventCommand,
    PublishDemoEventHandler,
)
from app.application.queries.health import HealthHandler, HealthQuery
from app.presentation.schemas import DemoEventRequest, DemoEventResponse


router = APIRouter(tags=["project"], route_class=DishkaRoute)


@router.get("/health", summary="Health check")
async def healthcheck(handler: FromDishka[HealthHandler]) -> dict:
    return await handler(HealthQuery())


@router.post(
    "/events/demo",
    response_model=DemoEventResponse,
    summary="Demo event flow",
)
async def publish_demo_event(
    payload: DemoEventRequest,
    handler: FromDishka[PublishDemoEventHandler],
) -> DemoEventResponse:
    result = await handler(
        PublishDemoEventCommand(
            topic="project.demo",
            payload=payload.payload,
        )
    )
    return DemoEventResponse(
        dispatched=result.dispatched,
        published=result.published,
        dispatch_error=result.dispatch_error,
        publish_error=result.publish_error,
    )
