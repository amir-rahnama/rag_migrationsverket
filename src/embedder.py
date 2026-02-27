"""Embedding using intfloat/multilingual-e5-large.

E5 models require specific prefixes:
  - Passages (documents):  "passage: <text>"
  - Queries:               "query: <text>"
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-large"
VECTOR_SIZE = 1024


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document passages."""
    model = _get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, batch_size=16)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    model = _get_model()
    embedding = model.encode([f"query: {query}"], normalize_embeddings=True)
    return embedding[0].tolist()
