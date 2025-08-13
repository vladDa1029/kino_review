from contextlib import asynccontextmanager
from typing import cast
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from app.application.use_case.exaptions import (
    InvalidCredentialsExaption,
    UserAlreadyExistsExaption,
)
from app.config import Auth, DatabaseSettings, Log, SQLAlchemySettings, get_settings
from app.dependens import setup_providers
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.exaptions.coder import NoValidTokenExption
from app.presentations.api import router as auth_router
from app.presentations import handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await cast("AsyncContainer", app.state.dishka_container).close()


def setup_start_test_app():
    config = get_settings()
    app = FastAPI(lifespan=lifespan, debug=True, title="Сервис авторизации.")

    context = {
        Log: config.log,
        Auth: config.auth,
        DatabaseSettings: config.db,
        SQLAlchemySettings: config.alchemy,
    }
    container = make_async_container(*setup_providers(), context=context)
    app.add_exception_handler(
        InvalidCredentialsExaption, handlers.invalid_credentials_exaption_handler
    )
    app.add_exception_handler(
        NoValidTokenExption, handlers.no_valid_token_exaption_handler
    )
    app.add_exception_handler(
        UserAlreadyExistsExaption, handlers.user_already_exists_exaption_handler
    )
    setup_dishka(container=container, app=app)
    start_mappers()

    # Настройка для разработки с React/Vue
    origins = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",  # Alternative
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Cache-Control",
        ],
        expose_headers=["Content-Disposition"],
    )
    app.include_router(auth_router)
    return app
