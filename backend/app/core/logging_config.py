import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logging() -> None:
    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
