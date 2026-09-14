"""Application-owned logging handlers; importing this module has no side effects."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_handlers: list[logging.Handler] = []
LOG_MAX_BYTES = 1_048_576
LOG_BACKUP_COUNT = 3


def configure_logging(log_file: str | Path | None = None, level: str = "INFO") -> None:
    logger = logging.getLogger("pythongame")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(
            path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8",
        ))
    shutdown_logging()
    logger.setLevel(level)
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    _handlers.extend(handlers)


def shutdown_logging() -> None:
    logger = logging.getLogger("pythongame")
    for handler in _handlers:
        logger.removeHandler(handler)
        handler.close()
    _handlers.clear()
