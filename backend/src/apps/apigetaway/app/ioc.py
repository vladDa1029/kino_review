from typing import Iterable
from dishka import Provider, Scope
from httpx import AsyncClient

from app.config import Services
from app.setup import get_aclient


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Services)
    return provider


def client_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(get_aclient, provides=AsyncClient)
    return provider


def auth_url_provider() -> Provider:
    provider = Provider(scope=Scope.APP)

    def get_auth_url(settings: Services) -> str:
        return settings.auth

    provider.provide(get_auth_url, provides=str, scope=Scope.APP)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (settings_provider(), client_provider(), auth_url_provider())
