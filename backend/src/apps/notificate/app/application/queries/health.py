from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthQuery:
    pass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    status: str
    service: str


class GetHealthHandler:
    async def __call__(self, query: HealthQuery) -> HealthStatus:
        return HealthStatus(status="ok", service="notificate")
