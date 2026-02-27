"""Parse sitemap1.xml and categorize URLs by type: html, pdf, docx, or skip."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
SKIP_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".csv",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
}


@dataclass
class SitemapEntry:
    url: str
    file_type: str  # "html" | "pdf" | "docx"
    lastmod: str | None = None


def _classify_url(url: str) -> str | None:
    """Return file type string or None if URL should be skipped."""
    lower = url.lower()
    for ext in SKIP_EXTENSIONS:
        if lower.endswith(ext):
            return None
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".docx"):
        return "docx"
    # Treat everything else (including /download/ paths without known ext) as html
    # unless it's a binary we know to skip
    if "/download/" in lower:
        # Unknown binary in download path — skip
        return None
    return "html"


def parse_sitemap(sitemap_path: str | Path) -> Iterator[SitemapEntry]:
    """Yield SitemapEntry for each URL that should be processed."""
    tree = ET.parse(sitemap_path)
    root = tree.getroot()

    for url_elem in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = url_elem.findtext(f"{{{SITEMAP_NS}}}loc", "").strip()
        lastmod = url_elem.findtext(f"{{{SITEMAP_NS}}}lastmod", None)
        if not loc:
            continue
        file_type = _classify_url(loc)
        if file_type is None:
            continue
        yield SitemapEntry(url=loc, file_type=file_type, lastmod=lastmod)


def load_all(sitemap_path: str | Path) -> list[SitemapEntry]:
    return list(parse_sitemap(sitemap_path))


if __name__ == "__main__":
    import sys
    from collections import Counter

    path = sys.argv[1] if len(sys.argv) > 1 else "sitemap.xml"
    entries = load_all(path)
    counts = Counter(e.file_type for e in entries)
    print(f"Total entries to process: {len(entries)}")
    for ftype, count in sorted(counts.items()):
        print(f"  {ftype}: {count}")
