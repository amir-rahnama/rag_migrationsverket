"""Chunk text, embed, and upsert into Qdrant."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.embedder import VECTOR_SIZE, embed_passages

COLLECTION_NAME = "migrationsverket"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=url)


def ensure_collection() -> None:
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


@dataclass
class DocumentChunk:
    text: str
    url: str
    title: str
    file_type: str
    chunk_index: int
    page_num: int | None = None


def _make_chunks(
    text: str,
    url: str,
    title: str,
    file_type: str,
    page_num: int | None = None,
) -> list[DocumentChunk]:
    raw_chunks = _splitter.split_text(text)
    return [
        DocumentChunk(
            text=chunk,
            url=url,
            title=title,
            file_type=file_type,
            chunk_index=i,
            page_num=page_num,
        )
        for i, chunk in enumerate(raw_chunks)
        if chunk.strip()
    ]


def index_document(
    text: str,
    url: str,
    title: str,
    file_type: str,
    pages: list[str] | None = None,
) -> int:
    """
    Chunk, embed, and upsert a document into Qdrant.
    For PDFs pass pages= list of page texts to preserve page metadata.
    Returns the number of chunks indexed.
    """
    ensure_collection()
    client = _get_client()

    all_chunks: list[DocumentChunk] = []

    if pages:
        for page_num, page_text in enumerate(pages, start=1):
            all_chunks.extend(
                _make_chunks(page_text, url, title, file_type, page_num=page_num)
            )
    else:
        all_chunks = _make_chunks(text, url, title, file_type)

    if not all_chunks:
        return 0

    texts = [c.text for c in all_chunks]
    vectors = embed_passages(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "url": chunk.url,
                "title": chunk.title,
                "text": chunk.text,
                "file_type": chunk.file_type,
                "chunk_index": chunk.chunk_index,
                "page_num": chunk.page_num,
            },
        )
        for chunk, vec in zip(all_chunks, vectors)
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)
