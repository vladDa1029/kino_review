class EventDispatcher:
    async def dispatch(self, topic: str, payload: dict) -> None:
        raise NotImplementedError
