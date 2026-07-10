"""
main.py — Entry point for the Espressif document downloader.

Usage:
    python main.py                      # download Datasheet + HW Guidelines + Errata
    python main.py --all                # same as default
    python main.py --datasheet          # Datasheets only
    python main.py --hardware           # Hardware Design Guidelines only
    python main.py --errata             # Errata only
    python main.py --family ESP32-S3    # filter by chip family
"""

import argparse
import sys
import time
import logging

import requests

from config import TARGET_DOC_TYPES, ESP_FAMILIES, DOWNLOADS_DIR, LOGS_DIR
from utils import setup_logging, ensure_dir, timestamp
from organizer import create_chip_structure
from scraper import discover_documents
from downloader import download_all
from browser import convert_html_to_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Espressif technical documents (Datasheet, HW Guidelines, Errata).",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    doc_group = parser.add_argument_group("Document type filters (default: all three)")
    doc_group.add_argument(
        "--all",
        action="store_true",
        help="Download Datasheet, Hardware Design Guidelines, and Errata (default behaviour)",
    )
    doc_group.add_argument(
        "--datasheet",
        action="store_true",
        help="Download Datasheets only",
    )
    doc_group.add_argument(
        "--hardware",
        action="store_true",
        help="Download Hardware Design Guidelines only",
    )
    doc_group.add_argument(
        "--errata",
        action="store_true",
        help="Download Errata only",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all matching documents without downloading anything",
    )

    parser.add_argument(
        "--family",
        metavar="CHIP",
        help=(
            "Limit download to a specific chip family "
            "(e.g. ESP32-S3).  Can be specified multiple times."
        ),
        action="append",
        dest="families",
    )

    return parser.parse_args()


def resolve_doc_types(args: argparse.Namespace) -> set[str]:
    """Return the set of doc-type names to download based on CLI flags."""
    if args.all or (not args.datasheet and not args.hardware and not args.errata):
        return set(TARGET_DOC_TYPES)

    selected: set[str] = set()
    if args.datasheet:
        selected.add("Datasheet")
    if args.hardware:
        selected.add("Hardware Design Guidelines")
    if args.errata:
        selected.add("Errata")
    return selected


def _print_document_list(documents: list) -> None:
    """Print a formatted table of all discovered documents, then a summary."""
    from collections import defaultdict
    from organizer import build_output_path

    # Group by chip → doc_type
    grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for doc in documents:
        grouped[doc.chip][doc.doc_type].append(doc)

    col_chip  = max(len(d.chip)     for d in documents)
    col_type  = max(len(d.doc_type) for d in documents)
    col_fmt   = 4  # "PDF" or "HTML"

    header = (
        f"{'CHIP':<{col_chip}}  {'TYPE':<{col_type}}  {'FMT':<{col_fmt}}  "
        f"{'EXISTS':<6}  TITLE / URL"
    )
    sep = "─" * min(len(header) + 40, 120)

    print(f"\n{sep}")
    print(header)
    print(sep)

    for chip in sorted(grouped):
        for doc_type in sorted(grouped[chip]):
            for doc in grouped[chip][doc_type]:
                fmt    = "HTML" if doc.is_html else "PDF "
                path   = build_output_path(doc)
                exists = "✓" if path.exists() and path.stat().st_size > 0 else "–"
                title  = doc.title[:55] + "…" if len(doc.title) > 55 else doc.title
                print(
                    f"{doc.chip:<{col_chip}}  {doc.doc_type:<{col_type}}  "
                    f"{fmt:<{col_fmt}}  {exists:<6}  {title}"
                )
                print(f"{'':>{col_chip + col_type + col_fmt + 14}}{doc.url}")

    print(sep)

    total   = len(documents)
    n_pdf   = sum(1 for d in documents if not d.is_html)
    n_html  = sum(1 for d in documents if d.is_html)
    n_done  = sum(
        1 for d in documents
        if build_output_path(d).exists() and build_output_path(d).stat().st_size > 0
    )
    print(
        f"\nTotal: {total}  |  PDF: {n_pdf}  HTML→PDF: {n_html}  "
        f"|  Already downloaded: {n_done}  Remaining: {total - n_done}\n"
    )


def main() -> int:
    args = parse_args()
    logger = setup_logging()

    ensure_dir(DOWNLOADS_DIR)
    ensure_dir(LOGS_DIR)

    doc_types = resolve_doc_types(args)
    families: list[str] | None = args.families  # None means "all families"

    logger.info("=" * 60)
    logger.info("Espressif Document Downloader")
    logger.info("Started at %s", timestamp())
    logger.info("Document types : %s", ", ".join(sorted(doc_types)))
    logger.info("Chip families  : %s", ", ".join(families) if families else "ALL")
    logger.info("=" * 60)

    # Pre-create folder structure
    chips_to_create = families if families else ESP_FAMILIES
    create_chip_structure(chips_to_create)

    # Discover documents (one family at a time if filtering, otherwise all)
    all_documents = []

    if families:
        for family in families:
            logger.info("\n── Scanning family: %s ──", family)
            docs = discover_documents(doc_types, family_filter=family)
            all_documents.extend(docs)
    else:
        all_documents = discover_documents(doc_types, family_filter=None)

    if not all_documents:
        logger.warning("No documents found. Check your network connection or try again later.")
        return 1

    # ── --list mode: print and exit ────────────────────────────────────────
    if args.list:
        _print_document_list(all_documents)
        return 0

    logger.info("\nTotal documents to process: %d", len(all_documents))

    # Separate PDF and HTML documents
    pdf_docs = [d for d in all_documents if not d.is_html]
    html_docs = [d for d in all_documents if d.is_html]

    logger.info("  PDF  : %d", len(pdf_docs))
    logger.info("  HTML : %d (will be converted to PDF via weasyprint)", len(html_docs))

    session = requests.Session()

    start = time.time()

    # Download PDF documents
    logger.info("\n── Downloading PDF documents ──")
    pdf_ok, pdf_fail = download_all(pdf_docs, session)

    # Convert HTML Errata to PDF
    html_ok, html_fail = 0, 0
    if html_docs:
        logger.info("\n── Converting HTML Errata to PDF ──")
        html_ok, html_fail = download_all(html_docs, session, html_converter=convert_html_to_pdf)

    elapsed = time.time() - start

    logger.info("\n" + "=" * 60)
    logger.info("Finished at %s", timestamp())
    logger.info("Elapsed     : %.1f s", elapsed)
    logger.info("Success     : %d", pdf_ok + html_ok)
    logger.info("Failures    : %d", pdf_fail + html_fail)
    logger.info("=" * 60)

    if pdf_fail + html_fail > 0:
        logger.info("Check logs/errors.log for details on failed downloads.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
