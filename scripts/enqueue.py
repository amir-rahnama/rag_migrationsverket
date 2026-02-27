"""
Seed all URLs from sitemap.xml into RQ queues.

Usage:
    python scripts/enqueue.py [--sitemap PATH] [--redis-url URL]

Queues:
    crawl    — HTML pages
    download — PDF / DOCX files

Idempotent: skips URLs whose output file already exists on disk OR whose job
is still live in Redis (pending/scheduled/started). Safe to re-run at any time.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from redis import Redis
from rq import Queue, Retry
from tqdm import tqdm

from src.crawler.sitemap_parser import load_all, SitemapEntry
from src.tasks import process_file_url, process_html_url

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"


def url_job_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def already_done(entry: SitemapEntry) -> bool:
    """Return True if the output file for this URL already exists on disk."""
    h = url_hash(entry.url)
    if entry.file_type == "html":
        return (DATA_DIR / "html" / f"{h}.txt").exists()
    elif entry.file_type == "pdf":
        return (DATA_DIR / "pdfs" / f"{h}.pdf").exists()
    elif entry.file_type == "docx":
        return (DATA_DIR / "docx" / f"{h}.docx").exists()
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enqueue crawl/download jobs from sitemap"
    )
    parser.add_argument("--sitemap", default="sitemap1.xml", help="Path to sitemap XML")
    parser.add_argument(
        "--redis-url", default=None, help="Redis URL (overrides REDIS_URL env)"
    )
    args = parser.parse_args()

    redis_url = args.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)

    crawl_q = Queue("crawl", connection=conn, default_timeout=120)
    download_q = Queue("download", connection=conn, default_timeout=300)

    entries = load_all(args.sitemap)
    print(f"Found {len(entries)} URLs to process")

    enqueued = skipped = 0

    for entry in tqdm(entries, desc="Enqueuing"):
        job_id = url_job_id(entry.url)

        # Skip if output file already on disk (most reliable idempotency check)
        if already_done(entry):
            skipped += 1
            continue

        # Also skip if job is still live in Redis (pending/scheduled/started)
        if conn.exists(f"rq:job:{job_id}"):
            skipped += 1
            continue

        if entry.file_type == "html":
            crawl_q.enqueue(
                process_html_url,
                entry.url,
                job_id=job_id,
                retry=Retry(max=3, interval=[10, 30, 60]),
            )
        else:
            download_q.enqueue(
                process_file_url,
                entry.url,
                entry.file_type,
                job_id=job_id,
                retry=Retry(max=3, interval=[10, 30, 60]),
            )
        enqueued += 1

    print(f"\nDone. Enqueued: {enqueued}  |  Already done (skipped): {skipped}")
    print("\nStart workers with:")
    print("  python scripts/worker.py")


if __name__ == "__main__":
    main()
