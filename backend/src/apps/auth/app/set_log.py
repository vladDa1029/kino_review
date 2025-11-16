import logging

from app.config import Log


import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder


def configure_logging(settings: Log) -> None:
    # отключение шумов от других библиотек
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    # Общие процессоры — добавляются ко всем логам
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

    # Процессоры для structlog (оборачивают логгер)
    structlog_processors = [
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    # Процессоры для logging (рендер в консоль)
    console_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(colors=True),
    ]

    # Настраиваем handler
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=common_processors,
            processors=console_processors,
        )
    )

    # Базовая конфигурация logging
    logging.basicConfig(
        handlers=[handler],
        level=settings.level.upper(),
        format=settings.format,  # structlog сам форматирует, это заглушка
    )

    # Конфиг structlog
    structlog.configure(
        processors=common_processors + structlog_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
