"""Offline reference parsing. Parsed sources still require manual approval."""

from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


def parse_reference(path: Path):
    if path.suffix.casefold() in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for node in soup.select("script, style, nav, header, footer"):
            node.decompose()
        content = soup.find("main") or soup
        return [
            {
                "section": "HTML main content",
                "page": None,
                "text": content.get_text("\n", strip=True),
            }
        ]
    if path.suffix.casefold() == ".pdf":
        result = []
        for page_number, page in enumerate(PdfReader(path).pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                raise ValueError(
                    "Scanned or empty PDF page requires a separately reviewed OCR ingestion path"
                )
            result.append({"section": f"Page {page_number}", "page": page_number, "text": text})
        return result
    if path.suffix.casefold() in {".txt", ".md"}:
        return [{"section": "Text", "page": None, "text": path.read_text(encoding="utf-8")}]
    raise ValueError("Unsupported reference format")


def token_chunks(text, tokenizer, max_tokens=220):
    # Keep complete paragraphs together. Oversize paragraphs are explicit review
    # failures, not silent truncation of contraindications or negations.
    chunks, group = [], []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(tokenizer.encode(paragraph, add_special_tokens=True)) > max_tokens:
            raise ValueError(
                "Paragraph exceeds token budget; split at meaningful boundaries and review"
            )
        candidate = "\n\n".join(group + [paragraph])
        if group and len(tokenizer.encode(candidate, add_special_tokens=True)) > max_tokens:
            chunks.append("\n\n".join(group))
            group = []
        group.append(paragraph)
    if group:
        chunks.append("\n\n".join(group))
    return chunks
