"""Chainlit chat interface for the Migrationsverket RAG system.

Run with:
    chainlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import chainlit as cl
from dotenv import load_dotenv

from src.generator import stream_answer
from src.retriever import format_context, search

load_dotenv()

TOP_K = 3


@cl.on_chat_start
async def on_start():
    await cl.Message(
        content=(
            "This is a RAG system based on publicly available Swedish data of the Migrationsverket (Migration Board). "
            "No commercial usage of this software is allowed. "
            "Please refer to the license of the software before usage.\n\n"
            "Ask me anything about Migrationsverket in any language.\n\n"
            "---\n"
            "© **Amir Rahnama** · CC BY-NC 4.0"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    query = message.content.strip()
    if not query:
        return

    # --- Retrieval ---
    results = search(query, top_k=TOP_K)

    if not results:
        await cl.Message(
            content="Jag hittade inga relevanta källor för din fråga."
        ).send()
        return

    context = format_context(results)

    # --- Streaming answer ---
    answer_msg = cl.Message(content="")
    await answer_msg.send()

    async for token in stream_answer(query, context):
        await answer_msg.stream_token(token)

    # --- Append sources as plain text after the answer ---
    seen_urls: set[str] = set()
    sources_text = "\n\n---\n**Sources:**\n"
    for i, r in enumerate(results, start=1):
        if r.url in seen_urls:
            continue
        seen_urls.add(r.url)
        title = r.title or "Untitled"
        score = f"{r.score * 100:.1f}%"
        page = f" · page {r.page_num}" if r.page_num else ""
        sources_text += f"\n{i}. **{title}**{page} ({score})\n   {r.url}\n"

    await answer_msg.stream_token(sources_text)
    await answer_msg.update()
