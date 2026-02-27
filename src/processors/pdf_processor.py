"""Extract text from PDF files using pdfplumber."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber


@dataclass
class ParsedPDF:
    url: str
    title: str
    pages: list[str] = field(default_factory=list)
    file_type: str = "pdf"

    @property
    def text(self) -> str:
        return "\n\n".join(self.pages)


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def process_pdf(url: str, file_path: str | Path) -> ParsedPDF:
    path = Path(file_path)
    title = path.stem.replace("_", " ").replace("-", " ")

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text(x_tolerance=2, y_tolerance=2)
            cleaned = _clean(raw)
            if cleaned:
                pages.append(cleaned)

    return ParsedPDF(url=url, title=title, pages=pages)
