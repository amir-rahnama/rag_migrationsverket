"""RQ task functions executed by workers.

Each task is a single unit of work:
  - process_html_url(url): fetch HTML → extract text → chunk + embed → index
  - process_file_url(url, file_type): download file → extract text → chunk + embed → index
"""

from __future__ import annotations

import logging

from src.crawler.file_downloader import download_file
from src.crawler.html_crawler import fetch_html
from src.indexer import index_document
from src.processors.docx_processor import process_docx
from src.processors.html_processor import HTML_DATA_DIR, process_html, save_html_text
from src.processors.pdf_processor import process_pdf

logger = logging.getLogger(__name__)


def process_html_url(url: str) -> dict:
    """
    RQ task: fetch an HTML page, save cleaned text to disk, and index into Qdrant.
    Skips the network request if a cached .txt already exists.
    Returns a summary dict on success; raises on failure (RQ captures traceback).
    """
    import hashlib

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    cached = HTML_DATA_DIR / f"{url_hash}.txt"

    if cached.exists():
        logger.info("Cache hit, loading from disk: %s", url)
        raw = cached.read_text(encoding="utf-8")
        # Parse out title and body from saved format
        lines = raw.split("\n", 3)
        title = lines[1].removeprefix("Title: ") if len(lines) > 1 else ""
        text = lines[3] if len(lines) > 3 else raw
        from src.processors.html_processor import ParsedDocument
        doc = ParsedDocument(url=url, title=title, text=text, file_type="html")
    else:
        logger.info("Crawling HTML: %s", url)
        raw_html = fetch_html(url)
        doc = process_html(url, raw_html)
        if doc.text.strip():
            save_html_text(doc)
            logger.info("Saved cleaned text to %s", cached)

    if not doc.text.strip():
        logger.warning("No text extracted from %s — skipping", url)
        return {"url": url, "chunks": 0, "skipped": True}

    n = index_document(
        text=doc.text,
        url=doc.url,
        title=doc.title,
        file_type=doc.file_type,
    )

    logger.info("Indexed %d chunks from %s", n, url)
    return {"url": url, "chunks": n}


def process_file_url(url: str, file_type: str) -> dict:
    """
    RQ task: download a PDF or DOCX and index it into Qdrant.
    Returns a summary dict on success; raises on failure.
    """
    logger.info("Downloading %s: %s", file_type.upper(), url)

    file_path = download_file(url, file_type)

    if file_type == "pdf":
        parsed = process_pdf(url, file_path)
        n = index_document(
            text=parsed.text,
            url=parsed.url,
            title=parsed.title,
            file_type=parsed.file_type,
            pages=parsed.pages,
        )
    elif file_type == "docx":
        parsed = process_docx(url, file_path)
        n = index_document(
            text=parsed.text,
            url=parsed.url,
            title=parsed.title,
            file_type=parsed.file_type,
        )
    else:
        raise ValueError(f"Unsupported file_type: {file_type}")

    logger.info("Indexed %d chunks from %s (%s)", n, url, file_type)
    return {"url": url, "file_type": file_type, "chunks": n}
