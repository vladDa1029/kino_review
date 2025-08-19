from contextlib import asynccontextmanager
from typing import cast
from dishka import AsyncContainer, make_async_container
from fastapi import FastAPI

from app.config import Services, get_settings
from app.ioc import setup_providers
from app.setup import CORS_Middleware
from app.presentation.api.v1.routes.auth import router as router_auth
from app.presentation.api.v1.routes.docs import router as router_docs
from dishka.integrations.fastapi import setup_dishka
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    # checkout all services

    yield
    await cast("AsyncContainer", app.state.dishka_container).close()


def start_app_dev():
    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="API Getaway",
        summary="Api Getaway",
        description="Сервис предаставляющий прокси всех микросервисов в виде API а также обрабатывает работу с токенами.",
    )

    container = make_async_container(*setup_providers(), context={Services: get_settings().services})
    setup_dishka(container=container, app=app)

    CORS_Middleware(app)
    app.include_router(router_docs)
    app.include_router(router_auth)
    return app
