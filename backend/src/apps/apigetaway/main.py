from contextlib import asynccontextmanager
from typing import cast
from dishka import AsyncContainer, make_async_container
from fastapi import FastAPI

from app.config import AuthGatewaySettings, ProtectedPathsSettings, Services, get_settings
from app.ioc import setup_providers
from app.setup import AuthGateway_Middleware, CORS_Middleware
from app.presentation.api.v1.routes.auth import router as router_auth
from app.presentation.api.v1.routes.docs import router as router_docs
from app.presentation.api.v1.routes.projects import router as router_projects
from app.presentation.api.v1.routes.users import (
    admin_router as router_admin_users,
    router as router_users,
)
from dishka.integrations.fastapi import setup_dishka


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

    settings = get_settings()
    container = make_async_container(
        *setup_providers(),
        context={
            Services: settings.services,
            AuthGatewaySettings: settings.auth_gateway,
            ProtectedPathsSettings: settings.protected_paths,
        },
    )
    setup_dishka(container=container, app=app)

    AuthGateway_Middleware(app, settings.auth_gateway, settings.protected_paths)
    CORS_Middleware(app)
    app.include_router(router_docs)
    app.include_router(router_auth)
    app.include_router(router_users)
    app.include_router(router_admin_users)
    app.include_router(router_projects)
    return app
