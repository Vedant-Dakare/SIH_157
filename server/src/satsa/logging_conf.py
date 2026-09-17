"""structlog JSON logging with run_id and entity_id bound context."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.typing import BindableLogger


def configure_logging(log_level: str, run_id: str, entity_id: str | None) -> BindableLogger:
    """Configure structlog JSON logging and return a bound logger.

    Args:
        log_level: Logging level name (e.g. "INFO").
        run_id: Run identifier bound to every log record.
        entity_id: Optional entity identifier bound to every log record.

    Returns:
        A structlog bound logger with run_id and entity_id context.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    context: dict[str, Any] = {"run_id": run_id}
    if entity_id is not None:
        context["entity_id"] = entity_id
    logger = structlog.get_logger().bind(**context)
    return logger  # type: ignore[no-any-return]
