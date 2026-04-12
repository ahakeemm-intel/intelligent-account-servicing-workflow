import sys
import os
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """Configure Loguru with console and file sinks."""
    logger.remove()  # Remove default handler

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )

    # Console sink
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # File sink — structured JSON for auditability
    log_path = settings.LOG_FILE
    if not os.path.isabs(log_path):
        log_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "../../../../", log_path)
        )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        serialize=False,
    )

    logger.info("Logging initialised | level={} | file={}", settings.LOG_LEVEL, log_path)
