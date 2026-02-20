import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name.

    Usage in any module:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)


def setup_logging(log_level: str = "INFO", log_file: str = "") -> None:
    """Call once at startup from main.py to configure logging globally."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in handlers:
        h.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=handlers, force=True)
