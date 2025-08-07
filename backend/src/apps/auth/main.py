from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.application.use_case.exaptions import InvalidCredentialsExaption
from app.config import get_settings
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.security.jwt import JWTServices
from app.presentations.api import router as auth_router
from app.presentations import handlers
from app.infrastructure import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_settings()
    # создаём подключение и настройку базы данных
    engine = None
    async for _engine in db.get_engine(config.db, config.alchemy):
        engine = _engine
        break

    if engine is None:
        raise RuntimeError("Не удалось создать engine")

    session_maker = await db.get_sessionmaker(engine, config.alchemy)

    # Создаём сервисы
    jwt_service = JWTServices(config=config.auth)

    # Кладём в состояние приложения
    app.state.engine = engine
    app.state.session_maker = session_maker
    app.state.jwt_service = jwt_service

    yield


def setup_start_test_app():

    app = FastAPI(lifespan=lifespan, debug=True)
    app.add_exception_handler(
        InvalidCredentialsExaption, handlers.invalid_credentials_exaption_handler
    )

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
