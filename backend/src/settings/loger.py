import logging

from config import get_settings



settings = get_settings()

def set_log():
    logging.basicConfig(
        level=getattr(logging, settings.log.level.upper(), logging.DEBUG),
        format=settings.log.format,
        handlers=[
            logging.StreamHandler(),
        ],
    )
