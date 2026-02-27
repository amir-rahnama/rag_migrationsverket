"""RAG retrieval: embed a query and return top-K chunks from Qdrant."""

from __future__ import annotations

import os
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint

from src.embedder import embed_query
from src.indexer import COLLECTION_NAME


@dataclass
class SearchResult:
    score: float
    url: str
    title: str
    text: str
    file_type: str
    chunk_index: int
    page_num: int | None


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=url)


def search(query: str, top_k: int = 5) -> list[SearchResult]:
    """
    Embed the query and return the top-K most relevant chunks.
    """
    vector = embed_query(query)
    client = _get_client()

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
        with_payload=True,
    )
    hits: list[ScoredPoint] = response.points

    results = []
    for hit in hits:
        p = hit.payload or {}
        results.append(
            SearchResult(
                score=hit.score,
                url=p.get("url", ""),
                title=p.get("title", ""),
                text=p.get("text", ""),
                file_type=p.get("file_type", ""),
                chunk_index=p.get("chunk_index", 0),
                page_num=p.get("page_num"),
            )
        )
    return results


def format_context(results: list[SearchResult]) -> str:
    """Format search results into a single context string for an LLM."""
    parts = []
    for i, r in enumerate(results, start=1):
        source = r.url
        if r.page_num:
            source += f" (page {r.page_num})"
        parts.append(f"[{i}] Source: {source}\nTitle: {r.title}\n\n{r.text}")
    return "\n\n---\n\n".join(parts)
