"""
Organizer: builds and returns the correct output path for each document.
"""

from pathlib import Path
from typing import NamedTuple

from config import DOWNLOADS_DIR
from utils import sanitize_folder_name, ensure_dir


class Document(NamedTuple):
    """Represents a single downloadable document."""

    chip: str
    doc_type: str
    title: str
    url: str
    is_html: bool = False


def build_output_path(doc: Document) -> Path:
    """
    Return the full path where the document file should be saved.

    Structure: downloads/<chip>/<doc_type>/<filename>
    """
    chip_dir = DOWNLOADS_DIR / sanitize_folder_name(doc.chip)
    type_dir = chip_dir / sanitize_folder_name(doc.doc_type)
    ensure_dir(type_dir)

    filename = _derive_filename(doc)
    return type_dir / filename


def _derive_filename(doc: Document) -> str:
    """Derive a safe filename from the document title and URL."""
    from utils import sanitize_filename

    if doc.is_html:
        return sanitize_filename(doc.title) + ".pdf"

    url_path = doc.url.split("?")[0].rstrip("/")
    url_filename = url_path.split("/")[-1]

    if url_filename.lower().endswith(".pdf"):
        return sanitize_filename(url_filename)

    safe_title = sanitize_filename(doc.title)
    return safe_title + ".pdf"


def create_chip_structure(chips: list[str]) -> None:
    """Pre-create the expected folder hierarchy for all chips."""
    from config import TARGET_DOC_TYPES

    for chip in chips:
        for doc_type in TARGET_DOC_TYPES:
            path = DOWNLOADS_DIR / sanitize_folder_name(chip) / sanitize_folder_name(doc_type)
            ensure_dir(path)
