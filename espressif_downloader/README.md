# Espressif Document Downloader

Automatically downloads Espressif technical documents — **Datasheets**, **Hardware Design Guidelines**, and **Errata** — for every ESP chip family.

## Features

- Auto-discovers all ESP chip families and documents from the Espressif website
- Filters only the three target document types; ignores everything else
- Streaming downloads with progress bars
- Retries failed downloads (3 attempts with exponential back-off)
- Skips already-downloaded files safely
- Converts HTML Errata pages to PDF using Playwright
- Logs all failures to `logs/errors.log`
- CLI flags for filtering by document type or chip family

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Run (downloads all three document types for all chips)
cd espressif_downloader
python main.py
```

## CLI Options

| Command | Effect |
|---------|--------|
| `python main.py` | Download Datasheet + HW Guidelines + Errata for all chips |
| `python main.py --all` | Same as above |
| `python main.py --datasheet` | Datasheets only |
| `python main.py --hardware` | Hardware Design Guidelines only |
| `python main.py --errata` | Errata only |
| `python main.py --family ESP32-S3` | Filter to ESP32-S3 (stackable) |
| `python main.py --datasheet --family ESP32` | ESP32 datasheets only |

## Output Structure

```
downloads/
    ESP32/
        Datasheet/
        Hardware Design Guidelines/
        Errata/
    ESP32-S2/
        ...
    ESP32-S3/
        ...
    (and so on for every discovered chip)

logs/
    errors.log
```

## Module Overview

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point, orchestration |
| `config.py` | All constants and settings |
| `scraper.py` | Discovers documents (API → DOM fallback) |
| `downloader.py` | Streaming downloads, retries, skip logic |
| `browser.py` | Playwright helpers (HTML→PDF, JS rendering) |
| `organizer.py` | Builds correct output file paths |
| `utils.py` | Logging setup, filename sanitization, helpers |

## Notes

- Playwright is required only for HTML Errata conversion and DOM fallback scraping.
- If the Espressif website's API format changes, adjust `scraper.py`.
- Re-running is safe: existing files are skipped automatically.
