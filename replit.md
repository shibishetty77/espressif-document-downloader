# Espressif Document Downloader

A Python automation tool that automatically downloads Espressif technical documents (Datasheets, Hardware Design Guidelines, Errata) for every ESP chip family.

## Run & Operate

```bash
cd espressif_downloader
python3 main.py                        # download all 3 doc types for all chips
python3 main.py --all                  # same as above
python3 main.py --datasheet            # Datasheets only
python3 main.py --hardware             # Hardware Design Guidelines only
python3 main.py --errata               # Errata only
python3 main.py --family ESP32-S3      # filter to one chip family
python3 main.py --datasheet --family ESP32-H2  # combine filters
```

## Stack

- Python 3.11
- `requests` — HTTP downloads (streaming, retry, skip-existing)
- `beautifulsoup4` + `lxml` — HTML scraping (no JavaScript required)
- `tqdm` — progress bars
- `weasyprint` — HTML→PDF conversion for HTML-based Errata/Guidelines

## Where things live

```
espressif_downloader/
    main.py          — CLI entry point and orchestration
    config.py        — All constants (URLs, doc types, retry settings)
    scraper.py       — Discovers documents from the Espressif website
    downloader.py    — Streaming PDF downloads with retry and skip logic
    browser.py       — HTML→PDF conversion using weasyprint
    organizer.py     — Builds correct output file paths
    utils.py         — Logging setup, filename sanitization
    requirements.txt — pip dependencies

downloads/           — All downloaded PDFs (auto-created)
    ESP32/
        Datasheet/
        Hardware Design Guidelines/
        Errata/
    ESP32-S2/  ...etc.

logs/
    errors.log       — Failed downloads logged here (never crashes)
```

## Architecture decisions

- **No hardcoded URLs** — all chip families and document links are scraped live from the Espressif website at runtime.
- **Server-side HTML, no JS needed** — the Espressif technical-documents page is Drupal 7 server-side rendered; plain `requests` + BeautifulSoup is sufficient (no Playwright for scraping).
- **weasyprint for HTML→PDF** — some Errata and HW Guidelines are HTML docs (ReadTheDocs/Sphinx). weasyprint renders them to PDF purely in Python without needing a browser binary.
- **Resume-safe** — `.part` temp files are used during streaming; existing files are skipped on re-run.
- **Chip family extraction** — regex strips module suffixes (MINI, WROOM, PICO…) to group all module variants under their parent chip (e.g. ESP32-H2-MINI-1 → ESP32-H2).

## Product

Downloads 83+ documents across 14+ chip families: ESP32, ESP32-S2/S3, ESP32-C2/C3/C5/C6/C61, ESP32-H2/H4, ESP32-P4, ESP8266, ESP8684, ESP8685. Runs in ~35 seconds for a single chip family; ~5–10 minutes for all chips.

## User preferences

_Populate as you build._

## Gotchas

- Run from inside `espressif_downloader/` directory (`cd espressif_downloader && python3 main.py`)
- `playwright install chromium` is in requirements but optional — weasyprint handles HTML→PDF without it
- weasyprint suppresses verbose CSS warnings at runtime (set to ERROR level)
- The Espressif page loads all 545+ documents in a single request (no pagination needed)
