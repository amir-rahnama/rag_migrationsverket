"""Download binary files (PDF, DOCX) to local data directory."""

from __future__ import annotations

import hashlib
import random
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.crawler.html_crawler import USER_AGENTS, MIN_DELAY, MAX_DELAY

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _build_session()


def _dest_path(url: str, file_type: str) -> Path:
    """Determine local destination path for a download URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = f".{file_type}"
    subdir = DATA_DIR / {"pdf": "pdfs", "docx": "docx"}.get(file_type, f"{file_type}s")
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"{url_hash}{ext}"


def download_file(url: str, file_type: str, timeout: int = 60) -> Path:
    """
    Download a file to the local data directory.
    Returns the local Path to the saved file.
    Raises RuntimeError on failure.
    """
    dest = _dest_path(url, file_type)
    if dest.exists():
        return dest

    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    }

    try:
        resp = _session.get(url, headers=headers, timeout=timeout, stream=True)
    except requests.RequestException as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        time.sleep(retry_after)
        resp = _session.get(url, headers=headers, timeout=timeout, stream=True)

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} downloading {url}")

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest
