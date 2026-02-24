from pydantic import BaseModel, Field


class DemoEventRequest(BaseModel):
    payload: dict = Field(default_factory=dict)


class DemoEventResponse(BaseModel):
    dispatched: bool
    published: bool
    dispatch_error: str | None = None
    publish_error: str | None = None
