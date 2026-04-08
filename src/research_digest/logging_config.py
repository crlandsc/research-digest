"""Logging configuration. Named logging_config to avoid shadowing stdlib logging."""

import logging
import os


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with consistent format.

    Level priority: explicit arg > LOG_LEVEL env > INFO default.
    """
    resolved = level or os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, resolved.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
