"""
Centralized logging setup. Import `configure_logging()` once at app
startup; every module then just does `logging.getLogger(__name__)` and
inherits this configuration — no per-file logging setup scattered around.
"""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return  # already configured (e.g. under pytest re-imports)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(handler)
