from contextlib import asynccontextmanager
from typing import cast

from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DatabaseSettings, Log, Rabbitmq, SQLAlchemySettings, get_settings
from app.domain.errors.base import ApplicationError
from app.ioc import setup_providers
from app.infrastructure.adapters.orm import start_mappers
from app.presentation import handlers
from app.presentation.api import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await cast(AsyncContainer, app.state.dishka_container).close()


def start_app_dev() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="User service",
    )
    settings = get_settings()
    container: AsyncContainer = make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            DatabaseSettings: settings.db,
            SQLAlchemySettings: settings.alchemy,
            Rabbitmq: settings.rabbitmq,
        },
    )
    setup_dishka(container=container, app=app)

    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    start_mappers()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8001",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Cache-Control"],
    )
    app.include_router(web_router)
    return app

