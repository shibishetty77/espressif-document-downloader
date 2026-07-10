"""
Scraper: discovers all ESP chips and their matching documents from the
Espressif technical-documents page.

The page is server-side rendered by Drupal 7, so no JavaScript / Playwright
is needed for discovery — plain requests + BeautifulSoup is sufficient.

Structure of each document row (tr.odd / tr.even inside .view-content):
  td.views-field-title        → div.SDK-title  → document title
  td.views-field-nothing      → span.file a    → PDF href  (PDF documents)
                              → span.link a    → HTML href (HTML Errata / HW guidelines)
"""

import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from config import BASE_URL, DOCUMENTS_URL, HEADERS
from organizer import Document
from utils import log_error, normalize_chip_name

logger = logging.getLogger("espressif_downloader")

# Map of keyword → canonical doc-type name
_DOC_TYPE_KEYWORDS: dict[str, str] = {
    "datasheet": "Datasheet",
    "hardware design guidelines": "Hardware Design Guidelines",
    "hardware design guideline": "Hardware Design Guidelines",
    "errata": "Errata",
}


def discover_documents(
    selected_doc_types: set[str],
    family_filter: str | None = None,
) -> list[Document]:
    """
    Main entry point.  Fetches the Espressif technical-documents page once
    and returns every Document that matches *selected_doc_types* (and the
    optional *family_filter*).
    """
    logger.info("Fetching %s …", DOCUMENTS_URL)

    session = requests.Session()
    try:
        response = session.get(DOCUMENTS_URL, headers=HEADERS, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        log_error(logger, "Failed to fetch the documents page", exc)
        return []

    html = response.text
    logger.info("Page fetched (%d bytes). Parsing …", len(html))

    docs = _parse_page(html, selected_doc_types, family_filter)

    logger.info("Discovered %d matching document(s).", len(docs))
    return docs


def _parse_page(
    html: str,
    selected_doc_types: set[str],
    family_filter: str | None,
) -> list[Document]:
    """Parse the full HTML page and return matching Document objects."""
    soup = BeautifulSoup(html, "lxml")

    view_content = soup.find(class_="view-content")
    if not view_content:
        logger.warning("Could not find .view-content in the page.")
        return []

    # All data rows (skip header row — it has <th> not <td>)
    rows: list[Tag] = [r for r in view_content.find_all("tr") if r.find("td")]

    logger.info("Found %d document rows in the page.", len(rows))

    docs: list[Document] = []
    for row in rows:
        doc = _parse_row(row, selected_doc_types, family_filter)
        if doc:
            docs.append(doc)

    return docs


def _parse_row(
    row: Tag,
    selected_doc_types: set[str],
    family_filter: str | None,
) -> Document | None:
    """
    Extract a Document from a single table row, or return None if the row
    does not match the requested filters.
    """
    # ── Title ──────────────────────────────────────────────────────────────
    title_div = row.find(class_="SDK-title")
    if not title_div:
        return None

    title = title_div.get_text(" ", strip=True)
    if not title:
        return None

    # ── Document type ───────────────────────────────────────────────────────
    doc_type = _classify_doc_type(title)
    if doc_type is None or doc_type not in selected_doc_types:
        return None

    # ── Chip / family ───────────────────────────────────────────────────────
    chip = _extract_chip(title)
    if not chip:
        return None
    chip = normalize_chip_name(chip)

    if family_filter:
        if family_filter.upper().replace("-", "") not in chip.upper().replace("-", ""):
            return None

    # ── Download URL ────────────────────────────────────────────────────────
    download_cell = row.find("td", class_=lambda c: c and "views-field-nothing" in c.split()
                             and "views-field-nothing-1" not in c.split())
    if not download_cell:
        # Fallback: last td
        cells = row.find_all("td")
        download_cell = cells[-1] if cells else None

    if not download_cell:
        return None

    link_tag = download_cell.find("a", href=True)
    if not link_tag:
        return None

    href = link_tag["href"].strip()
    if not href.startswith("http"):
        href = urljoin(BASE_URL, href)

    # Determine if the link is a PDF or an HTML page
    is_html = not href.lower().split("?")[0].rstrip("/").endswith(".pdf")

    return Document(
        chip=chip,
        doc_type=doc_type,
        title=title,
        url=href,
        is_html=is_html,
    )


def _classify_doc_type(title: str) -> str | None:
    """Return the canonical doc-type for a title, or None if not a target type."""
    lower = title.lower()
    for keyword, canonical in _DOC_TYPE_KEYWORDS.items():
        if keyword in lower:
            return canonical
    return None


_CHIP_PATTERN = re.compile(
    r"\b(ESP\d+(?:-[A-Z0-9]+)*)\b",
    re.IGNORECASE,
)

# Canonical chip sub-family suffixes (e.g. -S3, -C6, -H2, -P4)
# These are part of the family name and must NOT be stripped.
_FAMILY_SUFFIX_RE = re.compile(
    r"^(ESP\d+(?:-(?:S\d+|C\d+|H\d+|P\d+))?)",
    re.IGNORECASE,
)


def _extract_chip(title: str) -> str | None:
    """
    Extract the ESP chip *family* from a document title.

    Strategy: find the first ESP chip token, then keep only the root and
    one optional sub-family segment (S\d+, C\d+, H\d+, P\d+).

    Examples:
      "ESP32-S3-PICO-1 Datasheet"        → ESP32-S3
      "ESP8684-WROOM-05 Datasheet"        → ESP8684
      "ESP32-H2 Datasheet"               → ESP32-H2
      "ESP32-H2-MINI-1 Datasheet"        → ESP32-H2
      "ESP32-C3 Series SoC Errata"       → ESP32-C3
      "ESP32-C61 Datasheet"              → ESP32-C61
    """
    match = _CHIP_PATTERN.search(title)
    if not match:
        return None

    raw = match.group(1).upper()

    # Keep only root + optional one sub-family segment
    fm = _FAMILY_SUFFIX_RE.match(raw)
    return fm.group(1).upper() if fm else raw
