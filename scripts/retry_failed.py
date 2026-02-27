"""
Re-enqueue failed RQ jobs so they run again.

Usage:
    python scripts/retry_failed.py                      # retry ALL failed jobs
    python scripts/retry_failed.py --queue crawl        # only failed crawl jobs
    python scripts/retry_failed.py --queue download     # only failed download jobs
    python scripts/retry_failed.py --dry-run            # print what would be retried
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FailedJobRegistry

load_dotenv()

QUEUE_NAMES = ["crawl", "download"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry failed RQ jobs")
    parser.add_argument("--redis-url", default=None)
    parser.add_argument(
        "--queue",
        default=None,
        choices=QUEUE_NAMES,
        help="Limit retry to a specific queue (default: all queues)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print failed jobs without re-enqueuing",
    )
    args = parser.parse_args()

    redis_url = args.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)

    target_queues = [args.queue] if args.queue else QUEUE_NAMES
    total_retried = 0

    for queue_name in target_queues:
        queue = Queue(queue_name, connection=conn)
        registry = FailedJobRegistry(queue=queue)
        job_ids = registry.get_job_ids()

        if not job_ids:
            print(f"[{queue_name}] No failed jobs.")
            continue

        print(f"[{queue_name}] Found {len(job_ids)} failed job(s).")

        for job_id in job_ids:
            try:
                job = Job.fetch(job_id, connection=conn)
                exc_info = job.exc_info or "No traceback available"
                print(f"  Job {job_id[:12]}... | func={job.func_name}")
                if args.dry_run:
                    print(f"    Error: {str(exc_info)[:120]}")
                    continue

                # Re-enqueue into the original queue
                registry.requeue(job_id)
                total_retried += 1
                print(f"    → Re-enqueued")

            except Exception as e:
                print(f"  Could not fetch/retry job {job_id}: {e}")

    if not args.dry_run:
        print(f"\nTotal re-enqueued: {total_retried}")
        if total_retried:
            print("Make sure a worker is running: python scripts/worker.py")


if __name__ == "__main__":
    main()
