"""Extract clean text from raw HTML using BeautifulSoup."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

HTML_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "html"

STRIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript", "iframe"}


@dataclass
class ParsedDocument:
    url: str
    title: str
    text: str
    file_type: str = "html"


def _extract_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    if tag and tag.get_text(strip=True):
        return tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_body(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Prefer semantic content container
    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main-content")
        or soup.find(class_="content")
        or soup.body
    )

    if content is None:
        return ""

    text = content.get_text(separator="\n")
    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def process_html(url: str, raw_html: str) -> ParsedDocument:
    soup = BeautifulSoup(raw_html, "lxml")
    title = _extract_title(soup)
    text = _extract_body(soup)
    return ParsedDocument(url=url, title=title, text=text, file_type="html")


def save_html_text(doc: ParsedDocument) -> Path:
    """Save cleaned text to data/html/<url_hash>.txt. Returns the file path."""
    HTML_DATA_DIR.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.md5(doc.url.encode()).hexdigest()[:12]
    dest = HTML_DATA_DIR / f"{url_hash}.txt"
    content = f"URL: {doc.url}\nTitle: {doc.title}\n\n{doc.text}"
    dest.write_text(content, encoding="utf-8")
    return dest
