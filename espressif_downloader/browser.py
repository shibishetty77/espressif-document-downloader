"""
Browser: HTML-to-PDF conversion for Errata and Hardware Design Guidelines
that are served as HTML pages rather than PDFs.

Primary strategy  : weasyprint (pure Python, no browser required)
Fallback strategy : fetch the HTML with requests and pass it to weasyprint
"""

import logging
from pathlib import Path

import requests

from config import HEADERS
from organizer import Document, build_output_path
from utils import log_error

logger = logging.getLogger("espressif_downloader")


def convert_html_to_pdf(doc: Document) -> bool:
    """
    Download *doc.url* and render it to PDF using weasyprint.

    Returns True on success, False on failure (error is logged).
    """
    output_path = build_output_path(doc)

    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("  ✓ SKIP  %s (already exists)", output_path.name)
        return True

    logger.info("  → HTML→PDF: %s", doc.url)

    # 1. Try to find a direct PDF link on the page first (fastest)
    pdf_url = _find_pdf_link(doc.url)
    if pdf_url:
        logger.info("    Found embedded PDF link: %s", pdf_url)
        try:
            ok = _download_pdf(pdf_url, output_path)
            if ok:
                logger.info("  ✓ DONE  %s (embedded PDF)", output_path.name)
                return True
        except Exception as exc:
            log_error(logger, "Embedded PDF download failed; falling back to weasyprint", exc)

    # 2. Render with weasyprint
    return _weasyprint_convert(doc.url, output_path, doc.title)


def _find_pdf_link(page_url: str) -> str | None:
    """
    Fetch *page_url* and look for a direct PDF download link.

    ReadTheDocs pages expose a PDF link at:
    /_/downloads/<lang>/latest/pdf/
    or in the "on Read the Docs" sidebar flyout.
    """
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception:
        return None

    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    soup = BeautifulSoup(resp.text, "lxml")

    # ReadTheDocs flyout PDF link pattern
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "pdf" in href.lower() and ("download" in href.lower() or "/_/" in href):
            if not href.startswith("http"):
                href = urljoin(page_url, href)
            return href

    return None


def _download_pdf(url: str, output_path: Path) -> bool:
    """Stream a PDF from *url* to *output_path*."""
    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return False
        with open(output_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    return output_path.stat().st_size > 0


def _weasyprint_convert(url: str, output_path: Path, title: str) -> bool:
    """
    Fetch the HTML at *url* and render it to *output_path* using weasyprint.
    """
    try:
        import weasyprint  # noqa: PLC0415
    except ImportError:
        log_error(logger, "weasyprint not installed. Run: pip install weasyprint")
        return False

    try:
        # Suppress weasyprint's verbose CSS warnings
        import logging as _logging
        _logging.getLogger("weasyprint").setLevel(_logging.ERROR)
        _logging.getLogger("fontTools").setLevel(_logging.ERROR)

        wp = weasyprint.HTML(url=url)
        wp.write_pdf(str(output_path))

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info("  ✓ DONE  %s (weasyprint)", output_path.name)
            return True
        else:
            log_error(logger, f"weasyprint produced empty PDF for '{title}'")
            return False

    except Exception as exc:
        log_error(logger, f"weasyprint failed for '{title}'", exc)
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return False


def fetch_page_html(url: str) -> str:
    """
    Fetch a URL with requests and return the HTML text.
    Used as a lightweight alternative to Playwright for pages that
    don't require JavaScript rendering.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text
