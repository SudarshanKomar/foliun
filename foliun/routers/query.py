import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from foliun.auth import require_api_key
from foliun.config import get_settings
from foliun.db import get_db
from foliun.schemas import QueryRequest
from foliun.services.chunking import get_token_counter
from foliun.services.context import GROUNDING_PROMPT, construct_context, validate_citations
from foliun.services.embeddings import get_embedder
from foliun.services.llm import LlmClient, format_sse
from foliun.services.retrieval import RetrievalService, get_reranker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=None)
async def query(request: QueryRequest, db: Session = Depends(get_db)):
    """Run retrieval and stream a grounded answer."""

    settings = get_settings()
    llm = LlmClient(settings)
    rewrite_started = time.perf_counter()
    try:
        variants = await llm.rewrite_query(request.query, request.model)
    except Exception as exc:
        variants = []
        logger.warning("Query rewriting failed; using original query only", extra={"stage": "query_rewrite", "error": str(exc)})
    logger.info("Query rewrite completed", extra={"stage": "query_rewrite", "variant_count": len(variants), "duration_ms": round((time.perf_counter() - rewrite_started) * 1000, 2)})
    embedder = get_embedder()
    reranker = get_reranker()
    retrieval = RetrievalService(db, embedder, reranker, settings)
    result = await retrieval.retrieve(request.query, variants)
    if result.insufficient_context:
        return JSONResponse(status_code=200, content={"insufficient_context": True, "message": "No relevant documents found for your query."})
    counter = get_token_counter(settings)
    context, sources, total_tokens = construct_context(result.chunks, counter, settings)
    if not context:
        return JSONResponse(status_code=200, content={"insufficient_context": True, "message": "No relevant documents found for your query."})

    async def stream() -> object:
        answer_parts: list[str] = []
        try:
            async for token in llm.stream_answer(request.model, GROUNDING_PROMPT, context, request.query):
                answer_parts.append(token)
                yield format_sse("token", {"content": token})
            answer = "".join(answer_parts)
            invalid = validate_citations(answer, sources)
            if invalid:
                logger.warning("Citation validation failure", extra={"stage": "citation_validation", "invalid_citation_count": len(invalid)})
            for citation in invalid:
                yield format_sse("citation", citation)
            yield format_sse("done", {"sources_used": len(sources), "total_chunks_considered": result.total_candidates, "pipeline_latency_ms": result.latency_ms, "context_tokens": total_tokens})
        except Exception:
            yield format_sse("error", {"message": "LLM service temporarily unavailable"})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
