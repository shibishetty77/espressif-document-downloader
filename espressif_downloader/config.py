"""
Configuration constants for the Espressif document downloader.
"""

from pathlib import Path

BASE_URL = "https://www.espressif.com"
DOCUMENTS_URL = f"{BASE_URL}/en/support/documents/technical-documents"

API_URL = f"{BASE_URL}/en/support/documents/technical-documents"

DOWNLOADS_DIR = Path("downloads")
LOGS_DIR = Path("logs")
ERRORS_LOG = LOGS_DIR / "errors.log"

TARGET_DOC_TYPES = {
    "Datasheet",
    "Hardware Design Guidelines",
    "Errata",
}

ESP_FAMILIES = [
    "ESP32",
    "ESP32-S2",
    "ESP32-S3",
    "ESP32-C2",
    "ESP32-C3",
    "ESP32-C5",
    "ESP32-C6",
    "ESP32-H2",
    "ESP32-H4",
    "ESP32-P4",
]

DOWNLOAD_TIMEOUT = 60
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2
CHUNK_SIZE = 8192

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
