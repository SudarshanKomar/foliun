from pathlib import Path

from pypdf import PdfReader


class ExtractedText:
    """Extracted text with page metadata."""

    def __init__(self, text: str, page_offsets: list[tuple[int, int, int]], page_count: int | None) -> None:
        """Initialize extracted text."""

        self.text = text
        self.page_offsets = page_offsets
        self.page_count = page_count


def extract_text(path: Path, mime_type: str) -> ExtractedText:
    """Extract text from a PDF or TXT file."""

    if mime_type == "application/pdf":
        return extract_pdf_text(path)
    raw = path.read_text(encoding="utf-8")
    return ExtractedText(raw, [(1, 0, len(raw))], None)


def extract_pdf_text(path: Path) -> ExtractedText:
    """Extract text and page offsets from a PDF file."""

    reader = PdfReader(str(path))
    parts: list[str] = []
    offsets: list[tuple[int, int, int]] = []
    cursor = 0
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        start = cursor
        parts.append(page_text)
        cursor += len(page_text)
        offsets.append((index, start, cursor))
        parts.append("\n\n")
        cursor += 2
    return ExtractedText("".join(parts), offsets, len(reader.pages))
