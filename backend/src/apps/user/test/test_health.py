import asyncio

from app.presentation.api import healthcheck, router


def test_health_endpoint_returns_ok() -> None:
    assert asyncio.run(healthcheck()) == {"status": "ok"}


def test_health_route_is_registered() -> None:
    assert any(route.path == "/health" for route in router.routes)
