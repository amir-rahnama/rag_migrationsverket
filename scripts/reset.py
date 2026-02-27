"""
Reset the pipeline: clear Redis queues, Qdrant collection, and optionally local cache.

Usage:
    python scripts/reset.py                  # wipe Redis + Qdrant only
    python scripts/reset.py --cache          # also delete data/html, data/pdfs, data/docx
    python scripts/reset.py --dry-run        # show what would be deleted without doing it

After reset, re-run the full pipeline:
    python scripts/enqueue.py
    python scripts/worker.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from rq.registry import (
    DeferredJobRegistry,
    FailedJobRegistry,
    FinishedJobRegistry,
    ScheduledJobRegistry,
    StartedJobRegistry,
)

load_dotenv()

QUEUE_NAMES = ["crawl", "download"]
CACHE_DIRS = [
    Path("data/html"),
    Path("data/pdfs"),
    Path("data/docx"),
]


def reset_redis(conn: Redis, dry_run: bool) -> None:
    print("── Redis ──────────────────────────────")
    for name in QUEUE_NAMES:
        q = Queue(name, connection=conn)
        pending = len(q)
        registries = [
            FailedJobRegistry(queue=q),
            FinishedJobRegistry(queue=q),
            StartedJobRegistry(queue=q),
            ScheduledJobRegistry(queue=q),
            DeferredJobRegistry(queue=q),
        ]
        total_jobs = pending + sum(len(r) for r in registries)
        print(f"  [{name}] {total_jobs} jobs (pending={pending})")
        if not dry_run:
            q.empty()
            for reg in registries:
                for job_id in reg.get_job_ids():
                    try:
                        reg.remove(job_id, delete_job=True)
                    except Exception:
                        pass

    if not dry_run:
        print("  Redis queues cleared.")
    else:
        print("  [dry-run] Would clear all queues and job registries.")


def reset_qdrant(dry_run: bool) -> None:
    from qdrant_client import QdrantClient
    from src.indexer import COLLECTION_NAME

    print("── Qdrant ─────────────────────────────")
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=url)
    existing = {c.name for c in client.get_collections().collections}

    if COLLECTION_NAME not in existing:
        print(f"  Collection '{COLLECTION_NAME}' does not exist — nothing to drop.")
        return

    info = client.get_collection(COLLECTION_NAME)
    count = info.points_count
    print(f"  Collection '{COLLECTION_NAME}': {count} vectors")

    if not dry_run:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Collection '{COLLECTION_NAME}' deleted.")
    else:
        print(f"  [dry-run] Would delete collection '{COLLECTION_NAME}'.")


def reset_cache(dry_run: bool) -> None:
    print("── Local cache ────────────────────────")
    root = Path(__file__).parent.parent
    for d in CACHE_DIRS:
        full = root / d
        if not full.exists():
            print(f"  {d}: not found — skip")
            continue
        files = list(full.iterdir())
        print(f"  {d}: {len(files)} files")
        if not dry_run:
            shutil.rmtree(full)
            full.mkdir(parents=True)
            print(f"    → Cleared")
        else:
            print(f"    [dry-run] Would delete {len(files)} files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the RAG pipeline")
    parser.add_argument("--redis-url", default=None)
    parser.add_argument("--cache", action="store_true", help="Also wipe local cached files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — nothing will be deleted\n")

    redis_url = args.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)

    reset_redis(conn, args.dry_run)
    print()
    reset_qdrant(args.dry_run)

    if args.cache:
        print()
        reset_cache(args.dry_run)

    if not args.dry_run:
        print("\nDone. Now run:")
        print("  python scripts/enqueue.py")
        print("  python scripts/worker.py")


if __name__ == "__main__":
    main()
