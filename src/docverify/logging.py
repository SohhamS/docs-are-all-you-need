"""Structured logging.

Every log line inside a run should carry `run_id`, and inside a document
`doc_id`, and inside a claim `claim_id`. Without those you cannot answer
"what happened to this claim" from a log file, which is the only question
anyone asks a log file in this system.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog


def configure_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Set up structlog once, at process start."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)


@contextmanager
def bound(**kwargs: Any) -> Iterator[None]:
    """Bind ids for the duration of a block.

    Usage::

        with bound(run_id=run.id, claim_id=claim.id):
            ...
    """
    tokens = structlog.contextvars.bind_contextvars(**kwargs)
    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)
