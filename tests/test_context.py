import uuid

from foliun.config import Settings
from foliun.schemas import RetrievedChunk
from foliun.services.chunking import ApproximateTokenCounter
from foliun.services.context import construct_context, validate_citations


def make_chunk(document_id: uuid.UUID, index: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(content=content, document_id=document_id, document_title="doc", page_number=1, section_header=None, chunk_index=index, score=1.0)


def test_context_orders_by_document_position_and_respects_budget() -> None:
    document_id = uuid.uuid4()
    chunks = [make_chunk(document_id, 2, "two"), make_chunk(document_id, 1, "one"), make_chunk(document_id, 3, "word " * 20)]
    context, included, total_tokens = construct_context(chunks, ApproximateTokenCounter(), Settings(context_budget_tokens=12))
    assert "one" in context
    assert "two" in context
    assert included[0].chunk_index == 1
    assert total_tokens <= 12


def test_invalid_citation_detection() -> None:
    source = make_chunk(uuid.uuid4(), 0, "content")
    invalid = validate_citations("Answer [Doc: other, Page: 9]", [source])
    assert invalid == [{"title": "other", "page": "9"}]
