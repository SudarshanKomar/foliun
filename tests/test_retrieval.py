import uuid
from types import SimpleNamespace

from foliun.services.retrieval import SearchHit, reciprocal_rank_fusion


def make_hit(document_id: uuid.UUID, chunk_index: int, rank: int) -> SearchHit:
    chunk = SimpleNamespace(document_id=document_id, chunk_index=chunk_index, content="content", page_number=1, section_header=None)
    document = SimpleNamespace(id=document_id, filename="doc.txt")
    return SearchHit(chunk=chunk, document=document, rank=rank, similarity=1.0)


def test_rrf_uses_k_60_and_deduplicates() -> None:
    document_id = uuid.uuid4()
    duplicate_a = make_hit(document_id, 0, 1)
    duplicate_b = make_hit(document_id, 0, 2)
    other = make_hit(document_id, 1, 1)
    fused = reciprocal_rank_fusion([[duplicate_a, other], [duplicate_b]], k=60)
    assert len(fused) == 2
    assert fused[0].chunk.chunk_index == 0
    assert fused[0].rrf_score == (1 / 61) + (1 / 62)
