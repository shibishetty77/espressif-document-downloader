"""
Utility functions for the Espressif document downloader.
"""

import logging
import re
import sys
from pathlib import Path
from datetime import datetime

from config import LOGS_DIR, ERRORS_LOG


def setup_logging() -> logging.Logger:
    """Configure logging to both console and error log file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("espressif_downloader")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_format)

    file_handler = logging.FileHandler(ERRORS_LOG, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def sanitize_filename(name: str) -> str:
    """Remove or replace characters not safe for filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def sanitize_folder_name(name: str) -> str:
    """Sanitize a chip or document-type name for use as a directory name."""
    return sanitize_filename(name)


def ensure_dir(path: Path) -> Path:
    """Create directory and all parents; return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_doc_type(raw: str) -> str | None:
    """
    Normalize a raw document-type string from the website to one of
    the canonical target types, or return None if it is not a target.
    """
    from config import TARGET_DOC_TYPES

    raw_lower = raw.lower().strip()

    mapping = {
        "datasheet": "Datasheet",
        "hardware design guidelines": "Hardware Design Guidelines",
        "hardware design guideline": "Hardware Design Guidelines",
        "errata": "Errata",
    }

    for key, canonical in mapping.items():
        if key in raw_lower:
            return canonical

    return None


def normalize_chip_name(raw: str) -> str:
    """
    Normalize a raw chip/family name to a canonical form such as 'ESP32-S3'.
    """
    name = raw.strip()
    name = re.sub(r"\s+", "-", name)
    name = name.upper()
    name = re.sub(r"^ESPRESSIF[-\s]?", "", name)
    if not name.startswith("ESP"):
        name = "ESP" + name
    return name


def log_error(logger: logging.Logger, message: str, exc: Exception | None = None) -> None:
    """Log an error with optional exception details."""
    if exc:
        logger.error("%s — %s: %s", message, type(exc).__name__, exc)
    else:
        logger.error(message)


def timestamp() -> str:
    """Return a human-readable timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
