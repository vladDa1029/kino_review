import logging
from collections.abc import Iterable

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

from app.config import Log

NOISY_LIBRARY_LOGGERS: tuple[str, ...] = (
    "uvicorn",
    "uvicorn.access",
    "fastapi",
    "starlette",
    "aio_pika",
    "aiormq",
    "pamqp",
    "faststream",
    "taskiq",
)


def _set_log_level_for_loggers(loggers: Iterable[str], level: str) -> None:
    for logger_name in loggers:
        logging.getLogger(logger_name).setLevel(level.upper())


def configure_logging(settings: Log) -> None:
    common_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=True),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        CallsiteParameterAdder(
            [
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),
    ]

    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=common_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )
    )

    logging.basicConfig(
        handlers=[handler],
        level=settings.level.upper(),
        format=settings.format,
        force=True,
    )
    logging.captureWarnings(True)
    _set_log_level_for_loggers(NOISY_LIBRARY_LOGGERS, settings.third_party_level)

    structlog.configure(
        processors=common_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
