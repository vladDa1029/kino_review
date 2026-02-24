class EventPublisher:
    async def publish(self, topic: str, payload: dict) -> None:
        raise NotImplementedError
