import re
from dataclasses import dataclass

from transformers import AutoTokenizer

from foliun.config import Settings, get_settings


@dataclass(frozen=True)
class TextChunk:
    """Chunk produced by the chunking pipeline."""

    content: str
    token_count: int
    page_number: int | None
    section_header: str | None
    char_start: int
    char_end: int


class TokenCounter:
    """Token counting abstraction."""

    def __init__(self, model_name: str) -> None:
        """Initialize the BERT WordPiece tokenizer."""

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count(self, text: str) -> int:
        """Return token count for text."""

        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to a maximum number of tokens."""

        tokens = self.tokenizer.encode(text, add_special_tokens=False)[:max_tokens]
        return self.tokenizer.decode(tokens, skip_special_tokens=True)


class ApproximateTokenCounter:
    """Fallback token counter used when model tokenization is unavailable."""

    def count(self, text: str) -> int:
        """Return approximate token count for text."""

        return max(1, len(text.split()))

    def truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text approximately by whitespace tokens."""

        return " ".join(text.split()[:max_tokens])


def get_token_counter(settings: Settings | None = None) -> TokenCounter | ApproximateTokenCounter:
    """Return the configured token counter."""

    config = settings or get_settings()
    try:
        return TokenCounter(config.embedding_model_name)
    except Exception:
        return ApproximateTokenCounter()


def detect_section_header(text_before_chunk: str) -> str | None:
    """Detect a likely section header before a chunk."""

    lines = [line.strip() for line in text_before_chunk.splitlines() if line.strip()]
    for line in reversed(lines[-8:]):
        if len(line) <= 120 and re.match(r"^(\d+(\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:;()/-]+$", line):
            return line
    return None


def page_for_offset(char_start: int, page_offsets: list[tuple[int, int, int]]) -> int | None:
    """Return the source page number for a character offset."""

    for page_number, start, end in page_offsets:
        if start <= char_start <= end:
            return page_number
    return page_offsets[-1][0] if page_offsets else None


def split_text_into_chunks(
    text: str,
    page_offsets: list[tuple[int, int, int]],
    counter: TokenCounter | ApproximateTokenCounter,
    settings: Settings | None = None,
) -> list[TextChunk]:
    """Split extracted text into overlapping chunks."""

    config = settings or get_settings()
    clean_text = text.strip()
    if not clean_text:
        return []
    spans = [(match.start(), match.end(), match.group(0)) for match in re.finditer(r"\S+", clean_text)]
    chunks: list[TextChunk] = []
    start_word = 0
    while start_word < len(spans):
        end_word = start_word
        candidate = spans[start_word][2]
        while end_word < len(spans):
            start = spans[start_word][0]
            end = spans[end_word][1]
            candidate = clean_text[start:end]
            if counter.count(candidate) > config.chunk_size_tokens and end_word > start_word:
                end_word -= 1
                end = spans[end_word][1]
                candidate = clean_text[start:end]
                break
            end_word += 1
        if end_word >= len(spans):
            end_word = len(spans) - 1
            start = spans[start_word][0]
            end = spans[end_word][1]
            candidate = clean_text[start:end]
        token_count = counter.count(candidate)
        if token_count > config.chunk_size_tokens:
            candidate = counter.truncate(candidate, config.chunk_size_tokens)
            token_count = counter.count(candidate)
        char_start = spans[start_word][0]
        char_end = char_start + len(candidate)
        chunks.append(
            TextChunk(
                content=candidate,
                token_count=token_count,
                page_number=page_for_offset(char_start, page_offsets),
                section_header=detect_section_header(clean_text[:char_start]),
                char_start=char_start,
                char_end=char_end,
            )
        )
        if end_word >= len(spans) - 1:
            break
        start_word = max(start_word + 1, end_word - config.chunk_overlap_tokens + 1)
    return chunks
