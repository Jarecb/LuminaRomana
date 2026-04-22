"""Logging configuration helpers for Lumina Romana.

Provides a simple configure_logging function used during application startup to
set format and level.
"""
from __future__ import annotations

import logging


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
