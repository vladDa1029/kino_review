from app.config import TaskIQ
from taskiq_aio_pika import AioPikaBroker


def create_taskiq_broker(url: str, *, taskiq: TaskIQ) -> AioPikaBroker:
    return AioPikaBroker(
        url,
        exchange_name=taskiq.exchange_name,
        queue_name=taskiq.queue_name,
        dead_letter_queue_name=f"{taskiq.queue_name}.dead_letter",
        delay_queue_name=f"{taskiq.queue_name}.delay",
    )
