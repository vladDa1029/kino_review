from contextlib import asynccontextmanager
from typing import cast

from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.application.errors import AccessDeniedError
from app.config import (
    AuthGatewaySettings,
    Log,
    ProtectedPathsSettings,
    Services,
    get_settings,
)
from app.ioc import setup_providers
from app.presentation import handlers
from app.presentation.api.v1.routes.auth import router as router_auth
from app.presentation.api.v1.routes.docs import router as router_docs
from app.presentation.api.v1.routes.health import router as router_health
from app.presentation.api.v1.routes.projects import router as router_projects
from app.presentation.api.v1.routes.users import (
    admin_router as router_admin_users,
)
from app.presentation.api.v1.routes.users import (
    router as router_users,
)
from app.set_log import configure_logging
from app.setup import AuthGateway_Middleware, CORS_Middleware
import structlog
log = structlog.get_logger(__file__)
settings = get_settings()

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

    
    context ={
            Services: settings.services,
            AuthGatewaySettings: settings.auth_gateway,
            ProtectedPathsSettings: settings.protected_paths,
            Log: settings.log,
        }
    
    container = make_async_container(*setup_providers(), context=context)
    configure_logging(context[Log])
    setup_dishka(container=container, app=app)

    app.add_exception_handler(AccessDeniedError, handlers.access_denied_error_handler)
    AuthGateway_Middleware(app, settings.auth_gateway, settings.protected_paths)
    CORS_Middleware(app)
    app.include_router(router_health)
    app.include_router(router_docs)
    app.include_router(router_auth)
    app.include_router(router_users)
    app.include_router(router_admin_users)
    app.include_router(router_projects)
    log.info("Start application auth!!!")
    return app
