import asyncio
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from foliun.config import Settings, get_settings
from foliun.models import Chunk, Document, DocumentStatus
from foliun.schemas import RetrievalResult, RetrievedChunk
from foliun.services.embeddings import Embedder

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    """Vector search hit."""

    chunk: Chunk
    document: Document
    rank: int
    similarity: float
    rrf_score: float = 0.0
    rerank_score: float | None = None


class CrossEncoderReranker:
    """Cross-encoder reranker wrapper."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Load the cross-encoder model."""

        from sentence_transformers import CrossEncoder

        self.settings = settings or get_settings()
        self.model = CrossEncoder(self.settings.reranker_model_name)

    def score(self, query: str, chunks: list[SearchHit]) -> list[float]:
        """Score query/chunk pairs."""

        pairs = [(query, hit.chunk.content) for hit in chunks]
        raw_scores = self.model.predict(pairs)
        return [float(score) for score in raw_scores]


class RetrievalService:
    """Implement multi-query retrieval, RRF, and reranking."""

    def __init__(self, db: Session, embedder: Embedder, reranker: CrossEncoderReranker | None = None, settings: Settings | None = None) -> None:
        """Initialize retrieval service."""

        self.db = db
        self.embedder = embedder
        self.reranker = reranker
        self.settings = settings or get_settings()

    async def retrieve(self, query: str, variants: list[str]) -> RetrievalResult:
        """Retrieve ranked chunks for a query."""

        started = time.perf_counter()
        total_documents = self.db.scalar(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.ready))
        if not total_documents:
            return RetrievalResult(chunks=[], insufficient_context=True, reason="no_documents_indexed")
        queries = [query] + variants[:3]
        vectors = self.embedder.embed_texts(queries, is_query=True)
        search_tasks = [asyncio.to_thread(self._vector_search, vector, self.settings.retrieval_top_per_query) for vector in vectors]
        result_sets = await asyncio.gather(*search_tasks)
        fused = reciprocal_rank_fusion(result_sets, self.settings.retrieval_rrf_k)
        candidates = fused[: self.settings.retrieval_rerank_candidates]
        reranking_skipped = False
        if self.reranker and candidates:
            try:
                scores = await asyncio.wait_for(asyncio.to_thread(self.reranker.score, query, candidates), timeout=2)
                for hit, score in zip(candidates, scores, strict=False):
                    hit.rerank_score = score
                candidates.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
            except Exception as exc:
                reranking_skipped = True
                logger.warning("Cross-encoder reranking skipped", extra={"error": str(exc), "stage": "reranking"})
        else:
            reranking_skipped = True
        selected = candidates[: self.settings.retrieval_top_k]
        top_score = max((hit.rerank_score if hit.rerank_score is not None else hit.rrf_score for hit in selected), default=0.0)
        if not reranking_skipped and top_score <= self.settings.relevance_threshold:
            return RetrievalResult(chunks=[], insufficient_context=True, total_candidates=len(fused), latency_ms=round((time.perf_counter() - started) * 1000, 2))
        if selected:
            scores = [hit.rerank_score if hit.rerank_score is not None else hit.rrf_score for hit in selected]
            logger.info(
                "Retrieval completed",
                extra={"stage": "retrieval", "total_candidates": len(fused), "top_score": max(scores), "score_min": min(scores), "score_mean": statistics.mean(scores), "reranking_skipped": reranking_skipped},
            )
        return RetrievalResult(
            chunks=[to_retrieved_chunk(hit) for hit in selected],
            reranking_skipped=reranking_skipped,
            total_candidates=len(fused),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def _vector_search(self, vector: list[float], rank_limit: int) -> list[SearchHit]:
        """Run a pgvector cosine similarity search."""

        self.db.execute(text("SET LOCAL hnsw.ef_search = :ef_search"), {"ef_search": self.settings.hnsw_ef_search})
        rows = (
            self.db.query(Chunk, Document, Chunk.embedding.cosine_distance(vector).label("distance"))
            .join(Document, Chunk.document_id == Document.id)
            .filter(Document.status == DocumentStatus.ready, Chunk.embedding.is_not(None))
            .order_by(Chunk.embedding.cosine_distance(vector))
            .limit(rank_limit)
            .all()
        )
        hits: list[SearchHit] = []
        for index, row in enumerate(rows, start=1):
            chunk, document, distance = row
            hits.append(SearchHit(chunk=chunk, document=document, rank=index, similarity=1.0 - float(distance)))
        return hits


def reciprocal_rank_fusion(result_sets: list[list[SearchHit]], k: int = 60) -> list[SearchHit]:
    """Fuse search result rankings using Reciprocal Rank Fusion."""

    scores: dict[tuple[UUID, int], float] = defaultdict(float)
    hits_by_key: dict[tuple[UUID, int], SearchHit] = {}
    for result_set in result_sets:
        for hit in result_set:
            key = (hit.chunk.document_id, hit.chunk.chunk_index)
            scores[key] += 1 / (k + hit.rank)
            hits_by_key.setdefault(key, hit)
    fused = list(hits_by_key.values())
    for hit in fused:
        hit.rrf_score = scores[(hit.chunk.document_id, hit.chunk.chunk_index)]
    fused.sort(key=lambda item: item.rrf_score, reverse=True)
    return fused


def to_retrieved_chunk(hit: SearchHit) -> RetrievedChunk:
    """Convert a search hit to an API schema."""

    return RetrievedChunk(
        content=hit.chunk.content,
        document_id=hit.document.id,
        document_title=hit.document.filename.rsplit(".", 1)[0],
        page_number=hit.chunk.page_number,
        section_header=hit.chunk.section_header,
        chunk_index=hit.chunk.chunk_index,
        score=hit.rerank_score if hit.rerank_score is not None else hit.rrf_score,
        rrf_score=hit.rrf_score,
    )


@lru_cache
def get_reranker() -> CrossEncoderReranker:
    """Return the process-wide cross-encoder reranker."""

    return CrossEncoderReranker()
