"""
Start an RQ worker that processes crawl and download queues.

Usage:
    python scripts/worker.py [--redis-url URL] [--queues crawl download]

The worker processes queues in priority order (first listed = highest priority).
Failed jobs are stored in the RQ failed job registry and can be retried with
scripts/retry_failed.py.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start RQ worker")
    parser.add_argument("--redis-url", default=None)
    parser.add_argument(
        "--queues",
        nargs="+",
        default=["crawl", "download"],
        help="Queue names in priority order",
    )
    args = parser.parse_args()

    redis_url = args.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)

    queues = [Queue(name, connection=conn) for name in args.queues]
    queue_names = ", ".join(args.queues)
    print(f"Starting worker on queues: {queue_names}")
    print("Press Ctrl+C to stop gracefully.\n")

    worker = SimpleWorker(queues, connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
