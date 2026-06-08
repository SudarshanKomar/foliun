import re

from foliun.config import Settings, get_settings
from foliun.schemas import RetrievedChunk
from foliun.services.chunking import ApproximateTokenCounter, TokenCounter

GROUNDING_PROMPT = (
    "Answer the question using ONLY the provided context. "
    "Cite sources using [Doc: title, Page: N] format. "
    "If the answer is not present in the context, say that the documents do not contain enough information."
)


def construct_context(
    chunks: list[RetrievedChunk],
    counter: TokenCounter | ApproximateTokenCounter,
    settings: Settings | None = None,
) -> tuple[str, list[RetrievedChunk], int]:
    """Construct a token-budgeted context from retrieved chunks."""

    config = settings or get_settings()
    ordered = sorted(chunks, key=lambda chunk: (str(chunk.document_id), chunk.chunk_index))
    included: list[RetrievedChunk] = []
    parts: list[str] = []
    total_tokens = 0
    for chunk in ordered:
        page = chunk.page_number if chunk.page_number is not None else "N/A"
        part = f"[Source: {chunk.document_title}, Page: {page}]\n{chunk.content}"
        part_tokens = counter.count(part)
        if total_tokens + part_tokens > config.context_budget_tokens:
            continue
        parts.append(part)
        included.append(chunk)
        total_tokens += part_tokens
    return "\n\n".join(parts), included, total_tokens


def extract_citations(text: str) -> list[dict[str, str]]:
    """Extract citations from generated text."""

    citations: list[dict[str, str]] = []
    for match in re.finditer(r"\[Doc:\s*(?P<title>.*?),\s*Page:\s*(?P<page>[^\]]+)\]", text):
        citations.append({"title": match.group("title").strip(), "page": match.group("page").strip()})
    return citations


def validate_citations(answer: str, sources: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Return citations that do not match provided context sources."""

    allowed = {(source.document_title, str(source.page_number)) for source in sources}
    invalid: list[dict[str, str]] = []
    for citation in extract_citations(answer):
        if (citation["title"], citation["page"]) not in allowed:
            invalid.append(citation)
    return invalid
