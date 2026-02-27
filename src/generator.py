"""Generate answers using Ollama (qwen3:8b) with retrieved context."""

from __future__ import annotations

from typing import AsyncIterator

import ollama

try:
    from langdetect import detect as _detect_lang

    def detect_language(text: str) -> str:
        try:
            return _detect_lang(text)
        except Exception:
            return "en"

except ImportError:

    def detect_language(text: str) -> str:
        return "en"


LANGUAGE_NAMES = {
    "sv": "Swedish",
    "en": "English",
    "ar": "Arabic",
    "so": "Somali",
    "fa": "Farsi/Persian",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
}

MODEL = "qwen3:8b"

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about Migrationsverket (the Swedish Migration Agency).
Base your answer ONLY on the sources provided.
If the answer is not found in the sources, say so clearly.
Always cite the source URLs at the end of your answer."""


def build_prompt(query: str, context: str) -> str:
    lang_code = detect_language(query)
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())

    return f"""STRICT INSTRUCTION: Respond ONLY in {lang_name}. Do NOT use Chinese or any other language. Every word of your response must be in {lang_name}.

Sources:
{context}

Question: {query}

Response in {lang_name}:"""


async def stream_answer(query: str, context: str) -> AsyncIterator[str]:
    """Stream the LLM answer token by token."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(query, context)},
    ]

    stream = await ollama.AsyncClient().chat(
        model=MODEL,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        token = chunk.message.content
        if token:
            yield token
