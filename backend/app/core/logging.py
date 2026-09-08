"""Application-wide logging configuration. Call configure_logging() once at startup."""

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(*, level: int = logging.INFO) -> None:
    """Configure the root logger once; safe to call again (no duplicate handlers)."""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)
