import logging

from app.config import get_settings

settings = get_settings()


def set_logging_settings():
    logging.basicConfig(
        level=getattr(logging, settings.log.level.upper(), logging.DEBUG),
        format=settings.log.format,
        handlers=[
            logging.StreamHandler(),
        ],
    )
