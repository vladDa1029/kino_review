from taskiq_aio_pika import AioPikaBroker


def create_taskiq_broker(url: str) -> AioPikaBroker:
    return AioPikaBroker(url)
