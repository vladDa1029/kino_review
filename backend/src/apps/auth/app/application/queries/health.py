from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class HealthQuery:
    pass


class HealthHandler:
    async def __call__(self, query: HealthQuery) -> dict:
        return {"status": "ok"}
