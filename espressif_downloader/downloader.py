"""
Downloader: handles streaming downloads with progress bars, retries, and skip logic.
"""

import logging
import time
from pathlib import Path

import requests
from tqdm import tqdm

from config import (
    CHUNK_SIZE,
    DOWNLOAD_TIMEOUT,
    HEADERS,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
)
from organizer import Document, build_output_path
from utils import log_error

logger = logging.getLogger("espressif_downloader")


def download_document(doc: Document, session: requests.Session) -> bool:
    """
    Download a single document to its target path.

    Returns True on success, False on failure.
    Skips the download if the file already exists.
    """
    output_path = build_output_path(doc)

    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("  ✓ SKIP  %s (already exists)", output_path.name)
        return True

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            success = _stream_download(doc.url, output_path, session, doc.title)
            if success:
                return True
        except requests.exceptions.RequestException as exc:
            log_error(
                logger,
                f"Attempt {attempt}/{RETRY_ATTEMPTS} failed for '{doc.title}'",
                exc,
            )
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * attempt)

    log_error(logger, f"All {RETRY_ATTEMPTS} attempts failed for '{doc.title}' ({doc.url})")
    return False


def _stream_download(url: str, output_path: Path, session: requests.Session, label: str) -> bool:
    """
    Stream a file from *url* to *output_path*, showing a tqdm progress bar.

    Returns True on success.
    """
    with session.get(url, headers=HEADERS, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        desc = label[:60] + "…" if len(label) > 60 else label

        tmp_path = output_path.with_suffix(".part")
        try:
            with (
                open(tmp_path, "wb") as fh,
                tqdm(
                    total=total_size or None,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"  ↓ {desc}",
                    leave=False,
                ) as bar,
            ):
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        fh.write(chunk)
                        bar.update(len(chunk))

            tmp_path.rename(output_path)
            logger.info("  ✓ DONE  %s", output_path.name)
            return True

        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise


def download_all(
    documents: list[Document],
    session: requests.Session,
    html_converter: "callable | None" = None,
) -> tuple[int, int]:
    """
    Download every document in the list.

    For HTML Errata, delegate conversion to *html_converter* if provided.

    Returns (success_count, failure_count).
    """
    success = 0
    failure = 0

    for doc in documents:
        try:
            if doc.is_html and html_converter is not None:
                ok = html_converter(doc)
            else:
                ok = download_document(doc, session)

            if ok:
                success += 1
            else:
                failure += 1

        except Exception as exc:
            log_error(logger, f"Unexpected error downloading '{doc.title}'", exc)
            failure += 1

    return success, failure
