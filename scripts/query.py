"""
Interactive RAG query CLI.

Usage:
    python scripts/query.py
    python scripts/query.py --top-k 10
    python scripts/query.py --query "Vad krävs för att ansöka om uppehållstillstånd?"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def run_query(query: str, top_k: int) -> None:
    from src.retriever import format_context, search

    print(f"\nSearching for: {query!r}\n")
    results = search(query, top_k=top_k)

    if not results:
        print("No results found.")
        return

    print(f"Top {len(results)} results:\n")
    for i, r in enumerate(results, start=1):
        source = r.url
        if r.page_num:
            source += f" (page {r.page_num})"
        score_pct = f"{r.score * 100:.1f}%"
        print(f"[{i}] {score_pct} | {r.file_type.upper()} | {r.title or 'Untitled'}")
        print(f"     {source}")
        excerpt = r.text[:300].replace("\n", " ")
        print(f"     {excerpt}...")
        print()

    print("--- Context for LLM ---")
    print(format_context(results))


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the Migrationsverket RAG system")
    parser.add_argument("--query", "-q", default=None, help="Query string (skip interactive mode)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    if args.query:
        run_query(args.query, args.top_k)
        return

    print("Migrationsverket RAG — Interactive Query")
    print("Type 'exit' or press Ctrl+C to quit.\n")

    while True:
        try:
            query = input("Query> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            break

        try:
            run_query(query, args.top_k)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
