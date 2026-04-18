import asyncio
import logging
from typing import Any
from uuid import uuid4

from faststream.rabbit import RabbitQueue

log = logging.getLogger(__name__)


class BrokerReplyInbox:
    def __init__(self, service_name: str, instance_id: str | None = None) -> None:
        self.instance_id = instance_id or uuid4().hex
        self.reply_topic = f"{service_name}.reply.{self.instance_id}"
        self.queue_name = self.reply_topic
        self._futures: dict[str, asyncio.Future[dict[str, Any]]] = {}

    def register(self, correlation_id: str) -> None:
        if correlation_id in self._futures:
            raise ValueError(f"Reply wait is already registered for '{correlation_id}'.")
        self._futures[correlation_id] = asyncio.get_running_loop().create_future()

    async def wait_for(
        self,
        correlation_id: str,
        *,
        timeout: float,
    ) -> dict[str, Any]:
        future = self._futures.get(correlation_id)
        if future is None:
            raise RuntimeError(f"No pending reply registered for '{correlation_id}'.")
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._futures.pop(correlation_id, None)

    def resolve(self, correlation_id: str, payload: dict[str, Any]) -> bool:
        future = self._futures.get(correlation_id)
        if future is None:
            log.debug(
                "broker.reply.unmatched",
                extra={"correlation_id": correlation_id},
            )
            return False
        if future.done():
            log.debug(
                "broker.reply.duplicate",
                extra={"correlation_id": correlation_id},
            )
            return False
        future.set_result(payload)
        return True

    def discard(self, correlation_id: str) -> None:
        future = self._futures.pop(correlation_id, None)
        if future is not None and not future.done():
            future.cancel()


def build_reply_queue(inbox: BrokerReplyInbox) -> RabbitQueue:
    return RabbitQueue(
        name=inbox.queue_name,
        routing_key=inbox.reply_topic,
        durable=False,
        exclusive=True,
        auto_delete=True,
    )
